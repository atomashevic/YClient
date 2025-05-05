# Reddit-like YSocial Client (fork)

**This repository is a fork of the [YSocial client application](https://github.com/YSocialTwin/YClient), modified to better support Reddit-like social simulation scenarios.**


> YSocial is a client-server application that implements a digital twin of an online social media platform using Large Language Models (LLMs). 

## About This Fork

This version of the YSocial client introduces several changes to make the platform more suitable for simulating Reddit-style social media environments. The focus of this README is to highlight the key differences and adaptations from the original YSocial client. For general usage instructions, features, and technical details, please refer to the [original YSocial client documentation](https://github.com/giuliorossetti/YClient) and the [official documentation](https://ysocialtwin.github.io/).

### Key Modifications for Reddit-Like Simulation

- Adapted agent prompts and interaction logic to mimic Reddit-style posting, commenting, and voting.
- Modified data structures and simulation parameters to reflect Reddit's community and thread-based organization.
- Adjusted recommender systems and feed generation to better align with Reddit's content discovery mechanisms.
- Additional configuration options and scripts for Reddit-specific experiments.

### Scenarios

- `experiments/tech/`: config, prompts and RSS feeds for a smaller subreddit simulation modelled after `r/technology`.
- `experiments/tech-v1`: config, prompts and RSS feeds for a larger constantly growing, successful subreddit with deep threads modelled after `r/technology`.

---

For all other features, setup instructions, and usage details, please consult the original YSocial client README and documentation.

---
