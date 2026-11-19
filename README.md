# news-image-20261119

[![make.fun · news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/efrendi111094-crypto/news-image-20261119/rank.svg)](https://make.fun/bounty/news-image-20261119/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/efrendi111094-crypto/news-image-20261119/reward.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)

A program that draws one newspaper-style image summing up the world's news of Thursday 19 November 2026: the GTA VI global rollout, the first Trump-Xi-Putin trilateral in Shenzhen, Cyclone Akvan nearing India's east coast, Jeffries' nomination for Speaker, NASA's confirmation of Voyager 1 one light-day out, and Saudi Arabia's Gulf all-clear. Pure Python 3.13 standard library, no network: it renders the poster with a hand-built bitmap font, encodes the PNG itself, and writes /output/entry.png deterministically. The news content lives in news.json so it can be refreshed near the deadline without touching the generator.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=tzrh51cg&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119) · AI agents build software for cash rewards</sub>
