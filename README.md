How to setup your Python environment
------------------------------------

    sudo apt-get install pip-python
    sudo pip install virtualenv
    virtualenv ENV
    source ENV/bin/activate
    pip install -r requirements.txt

How to publish
--------------

    python publish.py src site

How to develop
--------------

python publish.py src site -w

Open browser at [localhost:8000]()
