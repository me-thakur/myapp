FROM docker:cli AS dockercli

FROM jenkins/jenkins:lts

USER root

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker

RUN apt-get update && \
    apt-get install -y curl unzip && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "/tmp/awscliv2.zip" && \
    unzip /tmp/awscliv2.zip -d /tmp && \
    /tmp/aws/install && \
    rm -rf /tmp/aws /tmp/awscliv2.zip /var/lib/apt/lists/*

USER jenkins
