Title: Machine learning facts
Category: Machine Learning
Summary: Some theoretical results in machine learning

A collection of foundational facts about machine learning that I have collected over the years. Some important, some not so much.

### Equivalences

* A Gaussian Process is a equivalent to a perceptron with a single hidden layer and an infinite number of hidden units [^GP]
* Any sub-cubic algorithm for parsing context-free grammars can be converted to a sub-cubic algorithm for Boolean Matrix multiplication [^CFGMatMul]


### Hardness

* It is NP-hard to minimise the number of non-zero parameters in a linear model, assuming the problem is separable [^L0Reg]
* It is NP-hard to do probabilistic inference in Bayesian networks [^NPBayes]
* It is NP-hard to _approximate_ probabilistic inference in Bayesian networks [^NPApproxBayesianInference]
* Non-negative matrix factorisation is NP-hard [^NNMF]

### The sad, sad tale of grammar inference

* It is NP-hard to find a minimum state DFA that matches a finite set of positive and negative examples [^MinDFA]
* It is NP-hard to find a minimum state DFA that matches a finite set of positive and negative examples, even with access to an oracle that can answer membership queries [^MinDFAOracle]
* It is cryptographically hard (equivalent to being able to break RSA) to PAC learn a minimum state DFA that matches a finite set of positive and negative examples [^MinDFAPAC]
* There is no polynomial-time algorithm to find a even an approximately minimum state DFA that matches a finite set of positive and negative examples (under P!=NP) [^ApproxMinDFA]


[^GP]: R. M. Neal. "Bayesian Learning for Neural Networks". Lecture Notes in Statistics 118, 1996.
[^L0Reg]: E. Amaldi and V. Kann. "On the approximability of minimizing non zero variables or unsatisfied relations in linear systems". Theoretical Computer Science, 1998.
[^NPBayes]: G. Cooper. "The Computational Complexity of Probabilistic Inference Using Bayesian Belief Networks" Artificial Intelligence 42, 1990.
[^NPApproxBayesianInference]: P. Dagum and M. Luby. Approximating probabilistic inference in Bayesian belief networks is NP-hard. Artificial Intelligence 60(1), 1993.
[^NNMF]: S. Vavasis. "On the complexity of nonnegative matrix factorization". COLT 2013.
[^CFGMatMul]: L. Lee. "Fast context-free grammar parsing requires fast Boolean matrix multiplication" Journal of the ACM 49(1), 2002.
[^MinDFA]: E M Gold. "Complexity of automaton identication from given data". Information and Control Volume 37 (3), 1978.
[^MinDFAOracle]: D. Angluin. "Queries and concept learning". Machine Learning Journal 2, 1987.
[^MinDFAPAC]: M. Kearns and L. Valiant. "Cryptographic Limitations on Learning Boolean Formulae and Finite Automata". STOC 1989.
[^ApproxMinDFA]: L. Pitt and M. Warmuth. "The Minimum Consistent DFA Problem Cannot be Approximated within any Polynomial". Journal of the Association for Computing Machinery 40(1), 1993.
