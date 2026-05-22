# Demo Questions

Use these in the recorded demo.

```bash
python src/main.py --profile sun_sign=Leo --profile moon_sign=Virgo --profile focus=study
```

```bash
python src/main.py --ask "What should I focus on for study and relationships today?" --date 2026-05-18 --trace
```

```bash
python src/main.py --ask "I feel nervous about deadlines. What does my memory and today's context suggest?" --date 2026-05-20 --trace
```

```bash
python src/main.py --ask "Give me a reflective weekly forecast, but explain which retrieved context you used." --date 2026-05-21 --trace
```

Good points to mention in the video:

- The agent retrieves domain knowledge, user memory, and time context before answering.
- The `--trace` output proves tool use.
- The memory file is updated after each forecast.
- The project can be extended with more IR tools.

## Chinese + BaZi Demo

```bash
python src/main.py --profile sun_sign=Leo --profile moon_sign=Virgo --profile focus=学习
```

```bash
python src/main.py --ask "我今天在学习、沟通和感情方面应该注意什么？也请结合八字和五行作为反思角度。" --date 2026-05-20 --trace
```

```bash
python src/main.py --ask "我的生日是2001年8月5日，我想关注学习、感情和八字五行。请根据这些信息给我今天的建议。" --date 2026-05-20 --trace
```

Point out in the video that the agent retrieves both Western astrology and BaZi knowledge, plus user memory and temporal context.
