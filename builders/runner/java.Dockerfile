FROM maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e

COPY warmup-pom.xml /tmp/quorum-warmup/pom.xml
COPY warmup-src /tmp/quorum-warmup/src

RUN mvn -B -ntp -f /tmp/quorum-warmup/pom.xml \
      -Dmaven.repo.local=/opt/maven-cache \
      dependency:go-offline package \
    && chmod -R a+rX /opt/maven-cache \
    && rm -rf /tmp/quorum-warmup

WORKDIR /src
