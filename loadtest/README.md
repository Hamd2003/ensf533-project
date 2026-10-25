# Load tests

k6 scripts that run the study's measurements against the 9 Lambda functions. No code changes needed: you run one command per round.

## Files

| File | What it does |
|---|---|
| `round.sh` | Runs a whole round: all 11 setups, in random order |
| `run.sh` | Runs one setup and saves its results; used by `round.sh` |
| `run.js` | The k6 test itself: sends requests, checks answers, records each one |
| `urls.json` | The function URLs. **Private**, ignored by git; get it from the repo owner |

## How it works

`./loadtest/round.sh restricted 1` does this:

1. **Shuffles the 11 setups** into a new random order (proposal §5) and saves the order.
2. For **each setup**, `run.sh` starts k6 with `run.js`, which:
   - looks up the setup: which function, and how many users at once (1, 3 or 8);
   - has each user send requests **back to back for 150 s**, with no pauses;
   - labels requests sent in the first **30 s as `warmup`**, which analysis ignores, and the rest as **`measure`**;
   - **checks every answer** against the correct one in `config/experiment.json`;
   - **writes one line per request** to the results file.
3. After each run, it prints `OK` or `!!! failed requests`, then **pauses 40 s** before the next setup.
4. At the end it prints the **`start` and `label`** to use for the AWS export.

A round takes about 35 minutes.

### The 11 setups

| Setups | Users | Answers |
|---|---|---|
| `api-512`, `api-1024`, `api-1769`, `cpu-512`, `cpu-1024`, `cpu-1769`, `data-512`, `data-1024`, `data-1769` | 3 | RQ1 (memory), RQ3 (workload type) |
| `cpu-1024-low`, `cpu-1024`, `cpu-1024-high` | 1, 3, 8 | RQ2 (users at once) |

These are the **`restricted`** user counts: the AWS account allows only 10 requests at once, so the proposal's 10 and 50 users don't fit (a plan adjustment). The `standard` profile has the proposal's counts, for when the limit is raised. Both are defined at the top of `run.js`.

## What gets saved

Everything for a round goes in **`results/round<N>/`**:

| File | Contents |
|---|---|
| `restricted-r1-<setup>.jsonl` | **One line per request:** response time (`duration_ms`), `status`, correct answer or not (`valid`), `phase` (warmup/measure), number of users, and AWS's `request_id` |
| `restricted-r1-<setup>.html` | **k6 dashboard report:** graphs of response time, requests per second and users. Open it in a browser. |
| `restricted-r1-order.txt` | The shuffled order and each run's start time (UTC) |
| `aws-export/` | The AWS-side data for the round (you add it after the round; see below) |

**k6 data vs AWS data:** the `.jsonl` files measure the full round trip from the laptop: network, plus AWS's front door, plus the function. The AWS export measures only the function inside AWS: execution time, billed time, memory used, cold starts and concurrency. `request_id` links each k6 line to its AWS line.

## Running a round

One-time setup:
- install k6 (`brew install k6` or `winget install k6`);
- put `urls.json` in this folder;
- use Terminal on Mac or **Git Bash** on Windows, and run commands from the repo's top folder.

1. **Tell the repo owner** a round is starting.
2. Run the round, then leave the laptop alone, plugged in and on the same wired network:
   ```sh
   ./loadtest/round.sh restricted 1      # then 2 and 3, on separate days
   ```
3. **Wait 10 minutes** after it ends.
4. **Export the AWS data:** GitHub → **Actions → export-aws-data → Run workflow**. Use the printed `start` (including **pm**) and `label`, and leave the rest as they are. Then download the export into the round's folder:
   ```sh
   gh run download $(gh run list --workflow export-aws-data.yml --limit 1 --json databaseId --jq '.[0].databaseId') \
     -n aws-data-restricted-round1 -D results/round1/aws-export
   ```

## Other commands

| Command | Use |
|---|---|
| `./loadtest/run.sh test api-512` | 20 s check with 1 user. Saved to `results/test/`, which git ignores; not study data. |
| `./loadtest/run.sh restricted 1 cpu-1024` | Redo one run of a round (delete its old `.jsonl` first) |
| `DASHBOARD=0 ./loadtest/round.sh …` | Skip the HTML reports |

## Rules

- **One run at a time for the whole team.** All runs share the AWS limit.
- **Same laptop and wired network** for every round.
- Never commit or post `urls.json` or a URL.
