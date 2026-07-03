# Building the real Mercury compiler (optional, advanced)

Mercury's compiler (`mmc`) is **not available as an apt package** on modern
Ubuntu/Debian and is not something `apt-cache search` will find beyond
unrelated packages that happen to share the name "mercury" (a SNES emulator
core, a mass-spectrometry tool). The only ways to get it are:

1. An **unofficial, untrusted PPA** (`ppa:altair-ibn-la-ahad/mercury-compiler`)
   -- not recommended for a production Docker image you don't control.
2. **Building from source**, which requires bootstrapping: Mercury's own
   compiler is written in Mercury, so you need an existing Mercury install (or
   a "release of the day" source+C bootstrap tarball) to build a new one. This
   routinely takes 30-60+ minutes and several hundred MB, which is likely to
   exceed Render's free/starter build time and image size limits.

Because of this, `determinism.py` in this folder honestly re-implements just
the determinism-classification concept in Python instead of shelling out to a
compiler that most deployments will never be able to install reliably.

If you still want to try a real build, roughly:

```dockerfile
FROM ubuntu:22.04 AS mercury-builder
RUN apt-get update && apt-get install -y build-essential wget flex bison
WORKDIR /mercury-src
RUN wget https://dl.mercurylang.org/release/mercury-srcdist-<version>.tar.gz \
    && tar xzf mercury-srcdist-<version>.tar.gz
WORKDIR /mercury-src/mercury-<version>
RUN ./configure --prefix=/opt/mercury && make -j$(nproc) && make install
```

...then copy `/opt/mercury` into the final image stage and add it to `PATH`.
Verify the exact current release URL at https://mercurylang.org/download.html
before use -- it changes per release and this file is not guaranteed current.
