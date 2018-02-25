From python:3.6.1

RUN apt-get update || exit 0
RUN apt-get upgrade -y
RUN apt-get install wget curl sudo procps vim gnupg -y

## Installing JAVA-8 for bazel build
RUN echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | sudo debconf-set-selections
RUN echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 seen true" | sudo debconf-set-selections
RUN echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main" | tee /etc/apt/sources.list.d/webupd8team-java.list
RUN echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main" | tee -a /etc/apt/sources.list.d/webupd8team-java.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EEA14886
RUN apt-get update
RUN apt-get install -y oracle-java8-installer

## Installing bazel build
RUN echo "deb [arch=amd64] http://storage.googleapis.com/bazel-apt stable jdk1.8" | sudo tee /etc/apt/sources.list.d/bazel.list
RUN curl https://bazel.build/bazel-release.pub.gpg | sudo apt-key add -
RUN sudo apt-get update && sudo apt-get install -y bazel

RUN apt-get install -y python3-numpy python3-dev python3-pip python3-wheel
RUN apt-get install -y git

RUN mkdir -p /code
WORKDIR /code
RUN git clone -b r1.5 https://github.com/tensorflow/tensorflow

ADD generate_packages_script.sh /code/tensorflow/

WORKDIR /code/tensorflow
