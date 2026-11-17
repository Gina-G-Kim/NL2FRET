FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends g++ make ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN curl -fsSL -o spot.tar.gz https://www.lrde.epita.fr/dload/spot/spot-2.16.1.tar.gz \
 && echo "182f4180da851588886a2e5f1540c3e2bb5cfddd228fd20689fa7ce498f57733  spot.tar.gz" | sha256sum -c - \
 && tar xzf spot.tar.gz && cd spot-2.16.1 \
 && ./configure --prefix=/opt/spot --disable-python --disable-devel --disable-doxygen --disable-static >/dev/null \
 && make -j2 >/dev/null && make install >/dev/null \
 && cd / && rm -rf /build
ENV PATH=/opt/spot/bin:$PATH
