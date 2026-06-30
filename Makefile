.PHONY: docs  dashboard forward
PYTHON=python3


requirements:
	mkdir -p docs recession_sos
	chmod 700 sec
	# chmod 600 sec/*
	# sudo apt install libfuse2
	# wget https://www.futunn.com/download/fetch-lasted-link?name=opend-ubuntu -o opend.tar.gz
	# tar zxvf opend.tar.gz
	# mv Futu_OpenD_9.2.5208_Ubuntu16.04 bin/
	# go to docs and see how to setup the opend
	# python3.11 -m venv .venv
	python -m ensurepip --upgrade
	python -m pip install --upgrade setuptools
	pip install --upgrade pip
	pip install -r requirements.txt

gitrcommit:
	git config http.postBuffer 524288000
	git config ssh.postBuffer 524288000
	-chmod 700 sec
	-chmod 600 sec/*
	chmod 600 recession_sos/*.py
	rm -rf .git/hooks/pre-push .git/hooks/post-push
	rm -rf .git/hooks/post-commit
	rm -rf .git/hooks/post-merge .git/hooks/post-checkout
	git config --global http.sslVerify false
	git config --global credential.helper store
	# git add -u
	git add Makefile 
	git add docs 
	-git commit -a -m "`date`"
	git pull --no-rebase
	git push origin HEAD

gitrupdate:
	rm -rf .git/hooks/pre-push .git/hooks/post-push
	rm -rf .git/hooks/post-commit
	rm -rf .git/hooks/post-merge .git/hooks/post-checkout
	git config --global http.sslVerify false
	git config --global credential.helper store
	git pull --no-rebase
	chmod 600 sec/*


run:
	python recession_sos/predict.py


