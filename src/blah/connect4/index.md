Title: Connect Four
Category: Games


The problem
===========

Here's the problem:

> Solve Connect Four, exactly, on a 2012 Macbook Air in no less than eight hours.

This is not a such a big challenge; Connect Four is a
[solved game](http://en.wikipedia.org/wiki/Connect_Four#Mathematical_solution),
this was shown independently by James Dow Allen and Victor Allis in the late
80s. The game turns out to be a win for the first player. You can use John Tromp's [Fhourstones](http://homepages.cwi.nl/~tromp/c4/fhour.html) ([github](https://github.com/qu1j0t3/fhourstones)) to compute an optimal strategy for you in about 10 minutes on my machine.

* It's interesting to do something even if someone has done it before.
* It's better tested and better explained
* I learned a lot about performance tuning algon the way
 
Sketch TOC
----------

* Minimax and alphabeta: pseudo-code
* Bitboards: micro-benchmarks for evaluate and isTerminal
* Caching: micro-benchmarks for get and set, given probe size (plus some reasonning about cache latency to a max-speed per node). Macro-benchmark for hash-map size, reduced problem, depth-based replacement scheme, max-depth
* Pruning: Macro-benchmarks for killer, history, LR symmetry, static move ordering, breadth-first filter
* Other optimisations
* Notes on testing
* Conclusion
* Appendix A: Improving alpha-beta
* Appendix B: Parallelising alpha-beta


Minimax
-------

The first step is the [Minimax](http://en.wikipedia.org/wiki/Minimax) algorithm for solving games.

    :::python
    def minimax(state):
        if state.is_terminal():
            return state.evaluate()
        else:
            value = VALUE_MAX if state.player == PLAYER_MIN else VALUE_MIN
            for child in state.children:
                child_value = minimax(child)
                if state.player == PLAYER_MAX:
                    value = max(child_value, value)
                else:
                    value = min(child_value, value)
            return value

The cost of the minimax algorithm in linear in the size of the game tree, but we can do better.

Diagram of the game tree

Alpha beta
----------

Minimax with upper/lower bounds.

    ::python
    def alpha_beta(state, alpha, beta):
        value = minimax(state)
        if value < alpha:
            return alpha
        elif value > beta:
            return beta
        else:
            return value

Alpha-beta has fewer responsibilities than minimax. It no longer needs
to return the value of a state, it just needs to return *bounds* on
the value of the state and that allows it to do the job faster. If it
can prove that the state falls outside the [alpha, beta] bound it can
stop early, or *cutoff* the search at that point.

An implementation of alpha-beta that takes advantage of this:

    ::python
    def alpha_beta(state, alpha, beta):
        if state.is_terminal():
            return state.evaluate()
        else:
            value = VALUE_MAX if state.player == PLAYER_MIN else VALUE_MIN
            for child in state.children:
                child_value = alpha_beta(child, alpha, beta)
                if state.player == PLAYER_MAX:
                    value = max(child_value, value)
                else:
                    value = min(child_value, value)

            return value

This is the basis of the solver, although we will add many optimisations before we have something that does what we want.

Bitboards
---------
We're going to be generating the tree as we iterate over it to keep
the memory budget small. This means we are going to be:

1. testing whether a state is terminal, and
2. generating all children of a state (if it's non-terminal)

for every state we explore.

One very efficient way to do (1) is to use a *bitboard* structure to
represent the pieces on the board. The idea is that we keep two 64-bit
numbers that record, for each position on the board, whether a piece
is present in that position for each player. Here's the layout on a
Connect Four board:

             0  1  2  3  4  5  6
           |XX|XX|XX|XX|XX|XX|XX|
        5  |05|12|19|26|33|40|47|
        4  |04|11|18|25|32|39|46|
        3  |03|10|17|24|31|38|45|
        2  |02|09|16|23|30|37|44|
        1  |01|08|15|22|29|36|43|
        0  |00|07|14|21|28|35|42|

There are two slightly odd things here. Firstly, the ordering goes up
by rows first and then columns, which perhaps seems a little less
natural that column first. The second is those `XX` positions, which
correspond to indexes in the bitboard that are specially reserved to
always contain a zero, called the zero barrier. We'll get into the
reasons for both in a little bit.

Here's an example board encoding:

      |.|.|.|.|.|.|.|
      |.|.|.|.|.|.|.|
      |.|.|.|.|.|.|.|
      |.|.|.|.|.|.|.|
      |.|.|.|.|.|.|.|
      |.|.|O|X|.|.|.|
    X = P1 (maximising player)
    O = P2 (minimising player)

    b1 = 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000
    b2 = 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000

One advantage of a bitboard is it's very compact so allocation and
copying of states is going to be cheap. The other big advatage is that
testing whether a state is terminal can be implemented very
efficiently with a handful of bitwise operations. To see this first
think about a bitboard `b` and the expression `(b << 2) & b`

     |.|.|.|.|.|.|.|     |.|.|X|.|X|.|.|     |.|.|.|.|.|.|.|
     |.|.|.|.|.|.|.|     |.|.|X|X|.|.|.|     |.|.|.|.|.|.|.|
     |.|.|X|.|X|.|.|     |.|.|X|X|X|X|.|     |.|.|X|.|X|.|.|
     |.|.|X|X|.|.|.|     |.|.|X|X|X|X|.|     |.|.|X|X|.|.|.|
     |.|.|X|X|X|X|.|     |.|.|.|.|.|.|.|     |.|.|.|.|.|.|.|
     |.|.|X|X|X|X|.|  &  |.|.|.|.|.|.|.|  =  |.|.|.|.|.|.|.|

As you can see, we have a bit set if there is a piece with another
pieces two positions to the left of it. Now let's do the trick again,
this time with a shift of one bit:

        |.|.|.|.|.|.|.|     |.|.|.|.|.|.|.|     |.|.|.|.|.|.|.|
        |.|.|.|.|.|.|.|     |.|.|X|.|X|.|.|     |.|.|.|.|.|.|.|
        |.|.|X|.|X|.|.|     |.|.|X|X|.|.|.|     |.|.|X|.|.|.|.|
        |.|.|X|X|.|.|.|     |.|.|.|.|.|.|.|     |.|.|.|.|.|.|.|
        |.|.|X|.|.|.|.|     |.|.|.|.|.|.|.|     |.|.|.|.|.|.|.|
        |.|.|X|X|.|.|.|  &  |.|.|.|.|.|.|.|  =  |.|.|.|.|.|.|.|

The final result will have a 1 in any position where there is a column
of four pieces. If we were to shift by the increments of the height of
the board instead of one, we can detect rows of four pieces and
shifting by `height+1` and `height-1` deals with diagonal lines of
four pieces.

This is where we get to the zero barrier, that row of zero bits across
the top.

We also need to check for a draw, which is just a bitwise OR of the
two bitboards and a comparison against a full bitboard.

Column order to keep track of height for each column, for quicker
move(). Probably could be quicker still (why it's column major)

(Benchmark results)

Summary:
 * 64-bit bitboards, state is 21 bytes
 * Testing for terminal states in ~20ns
 * Making new states in ~20ns

Caching states
--------------

The same state can be arrived at through different sequence of moves

    |.|.|.|.|.|.|.|
    |.|.|.|.|.|.|.|
    |.|.|.|.|.|.|.|
    |.|.|.|.|.|.|.|
    |.|.|O|.|X|.|.|
    |.|.|X|.|O|.|.|

In this state, the first move must be the `X` in column 2, the second
move, however, could be either in column 2 or column 4 so this state
can be reached by two different paths in the game tree. We will be
doing a considerable amount of redundant work in working on states
that can be reached multiple ways in the game tree - at lower depths
the number of paths to reach the same state will be very large.

The approach we take here is to use a large cache structure that
stores states and their values. This is a common strategy in chess
programming, where they call it a *transposition table*, but I'm just
going to call it a cache.

The cache is implemented as a very simple hash table, using a fixed
size, closed addressing and linear probing to resolve hash collisions.
The nice thing about using a hash table as a cache is that we don't
have to care too much about occasional false negatives so we used a
fixed size probe and just give up after that if we don't find what we
want. This maintains a constant cost for lookup even when the hash
table gets full (although the hit rate goes down a lot).

 * Hash function (Incremental Zobrist)
 * Key/value structure
 * Key trick
 * Depth based replacement
 * Performance evaluation
 * PSA: CPU utilisation / cache misses
 * Max depth

Summary:

 * Very simple hash table implementation
  * fixed size,
  * fixed size linear probing to resolve collisions,
  * possibility of false negatives
 * Depth based replacement
 * Incremental hashing

Pruning
-------

The last major thing we can do to improve performance is to make the
pruning of states more effective.

For example, starting from a empty Connect Four board, let's assume
player 1 puts their first piece in the central column. Solving from
this state you can show that player 1 can force a win from this state,
so you can terminate your search without evaluating any other states
because you can't get better than winning the game. If you were
instead to explore all first move positions from left to right, you
would do a lot of work evaluating the first three columns before you
found the winning move.

The principle here is that some traversal orders are better than
others and the best orders are the ones where the first move explored
guarantees a win for either player. Of course, the catch is if you knew the
moves which would result in a win ahead of time, you would have solved
the whole problem already. The best we can do is work out cheap
heuristic functions which tend to identify moves that are likely to
result in cutoffs and explore them first.

The first thing we can do is to determine if any child is a winning
state before we start doing the expensive evaluation step on each
child.

    ::python
    for child in state.children:
        if child.evaluate() == WIN_P1 and state.player() == P1:
           return WIN_P1
        elif child.evaluate() == WIN_P2 and state.player() == P2:
           return WIN_P2

A second idea - taking inspriation from the example above - is to
explore the central columns first before trying the columns further
away from the centre. This is based on the intuition that these moves
are more valuable because there are more ways to connect a piece in
the centre in a line of four than there are for a piece in a corner.

A well-known technique to get a better move ordering in chess programming
is the [killer heuristic](http://en.wikipedia.org/wiki/Killer_heuristic). This is a
very simple heuristic where you keep track of the last move that
caused a cutoff at the depth you are currently and pick that as your
first move to explore. The idea is that the tree has some kind of
locality where a good move for one state will be a good move for its
sibling states since they are likely to be very similar.

Another move ordering technique is the [history heuristic] where you
keep a record of how many times a move in each column has caused a
cutoff at any depth.

One way of reducing the search space, similar to the state
cache mentioned before is to exploit symmetries in the game state. If
you were to mirror the board along the central column you would have a
state that would have the exact same value. We can mirror a bitboard
fairly quickly and make a second check in our cache for the mirrored
board, effectively reducing the state space by a factor of two.

Another way of obtaining a good move ordering is iterative deepening.

Ordering                | Speedup
------------------------|---------
Killer heuristic        |  10x
LR symmetry             |  20x
Iterative deepening     |   5x
Central bias            |   2x
Evaluation to depth 1   | 0.5x


Summary:

 * First sweep on children to test for winning moves
 * Static move ordering, biased to the central column
 * Killer heuristic reordering to promote the killer move

Other optimisations
===================

The tree things above were the major factors in getting the runtime
down, however there were a few other things that helped to a smaller
degree:

  * Prefetching before cache access
    1234
  * Memory pooling for the states
    Surprising
  * Using a sorting network for the move reordering
    You could probably do it better but sorting approach is very
    flexible. Ended up using very little time.
  * -O3 -ftree-vectorise
    Got us about 10%
  * Better reporting of the state of evaluation
    Tracking things like cache utilisation, average index of cutoffs,
    etc helped a lot
  * Profilers
    Valgrind, instruments

End of the day 60% of the time is in get/put, 30% in children and
evaluate and the rest went somewhere else.

Conclusion
==========

 * Harder than I thought, mostly an implementation exercise
 * A game of orders of magnitude, speedups of any less that 5x not
   really worth the time
 * Pruning is king


Appendix A: Improving alpha-beta
--------------------------------

If you look at things written about chess programming, the most
promising improvements to alpha-beta are either parallelisation of
regular alpha-beta or an algorithm called MTD(f) which is supposed to
be more efficient.

Parallelisation of alpha-beta is not a particularly straightforward
thing. The introduction of a pruning step after exploring each child
state makes the algorithm explicitly serial, that's why it's fast in
the first place. In order to be able to parallelise alpha-beta you
have to be willing to give up on (at least some of) that pruning.

For me, MTD(f) was not an algorithm that made a lot of sense to me,
even after reading several detailed explanations. However, as
sometimes happens, the original paper on the algorithm gives by far
the best explanation of MTD(f). My brief summary is this: alpha-beta
is fastest when the space between alpha and beta is small (called the
search window). A small search window means more cutoffs and a smaller
time to complete but is also likely to be unhelpful if the true value
doesn't lie between alpha and beta.

End of the day 60% of the time is in get/put, 30% in children and
evaluate and the rest went somewhere else.
