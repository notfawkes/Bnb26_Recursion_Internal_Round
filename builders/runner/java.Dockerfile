FROM maven:3.9.9-eclipse-temurin-21

COPY warmup-pom.xml /tmp/quorum-warmup/pom.xml
COPY warmup-src /tmp/quorum-warmup/src

RUN mvn -B -ntp -f /tmp/quorum-warmup/pom.xml \
      -Dmaven.repo.local=/opt/maven-cache \
      dependency:go-offline package \
    && chmod -R a+rX /opt/maven-cache \
    && rm -rf /tmp/quorum-warmup

WORKDIR /src
