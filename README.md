# Computer Vision Attention Monitoring

[![CI](https://github.com/awasthiprashast/computer-vision-attention-monitoring/actions/workflows/ci.yml/badge.svg)](https://github.com/awasthiprashast/computer-vision-attention-monitoring/actions/workflows/ci.yml)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A real-time, privacy-preserving attention monitor for online learning. A student's webcam is analysed
**on their own machine** with MediaPipe, and only a few numbers (an attention score, eye openness, head
direction) are sent to a cloud backend. Teachers see live trends and PDF reports in a dashboard.
**No video or images ever leave the student's computer.**

![Dashboard with demo data](docs/images/dashboard.jpg)

*The dashboard, shown with synthetic demo data (`scripts/seed_demo_data.py`).*

## Features

- **Edge processing:** MediaPipe FaceMesh runs locally; the client computes the score and sends numbers only.
- **Eye Aspect Ratio (EAR) scoring** combined with a head-direction estimate, smoothed over recent frames, with a
  short **per-user calibration** at the start of each session.
- **FastAPI backend** with validation, optional API-key authentication and a PostgreSQL time series.
- **Streamlit dashboard** with auto-refresh, per-student filtering and summaries, and PDF reports
  (downloadable, with optional upload to S3).
- **One-command local stack** with Docker Compose, plus a demo-data generator so you can try it without a webcam.
- **AWS deployment as code:** Terraform for a VPC, EC2, RDS PostgreSQL, S3, IAM and SSM secrets.
- **Tests and CI:** 33 tests, ruff linting, Terraform validation and Docker builds in GitHub Actions.

## Architecture

```mermaid
flowchart LR
    subgraph student["Student laptop"]
        cam[Webcam] --> mp[MediaPipe FaceMesh]
        mp --> score["Scoring (EAR + head direction)"]
    end
    score -- "HTTP POST /attention (numbers only)" --> api[FastAPI backend]
    api --> db[(PostgreSQL)]
    db --> dash[Streamlit dashboard]
    dash -- "PDF reports (optional)" --> s3[(S3)]
    teacher([Teacher]) --> dash
```

The same design runs locally under Docker Compose and on AWS (EC2 for the backend and dashboard, RDS for the
database, S3 for reports). See [docs/deployment.md](docs/deployment.md).

## Quick start (no webcam, no cloud account)

Requires Docker.

```bash
git clone https://github.com/awasthiprashast/computer-vision-attention-monitoring
cd computer-vision-attention-monitoring
docker compose up -d --build
python scripts/seed_demo_data.py        # synthetic students and sessions
```

Open the dashboard at <http://localhost:8501> and the API docs at <http://localhost:8000/docs>.
Stop with `docker compose down` (add `-v` to delete the database).

## Running the real client

The client needs a webcam and Python 3.10-3.12 (developed on 3.11).

```bash
cd client
pip install -r requirements.txt
```

Then set the configuration and run it. In bash:

```bash
STUDENT_ID=alice API_URL=http://localhost:8000/attention python attention_client.py
```

In PowerShell:

```powershell
$env:STUDENT_ID="alice"; $env:API_URL="http://localhost:8000/attention"; python attention_client.py
```

On start the client spends about 3 seconds **calibrating**: look at the screen normally and blink as usual.
Nothing is sent during this phase. Press `c` in the video window to recalibrate (for example after moving or
changing the lighting) and `q` to quit. If the face leaves the frame, nothing is scored or sent until it returns.

## Configuration

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `STUDENT_ID` | client | `student_001` | Identifier attached to every reading |
| `API_URL` | client, seed script | `http://localhost:8000/attention` | Backend endpoint |
| `API_KEY` | client, backend, seed script | empty | Shared secret sent as `X-API-Key`. Empty disables auth (development only) |
| `SEND_INTERVAL` | client | `1.0` | Seconds between readings |
| `CALIBRATE` | client | `1` | Set to `0` to skip calibration and use a fixed default scale |
| `DATABASE_URL` | backend, dashboard, `scripts/db_check.py` | none (dashboard) | SQLAlchemy URL, e.g. `postgresql://user:pass@host:5432/db` |
| `S3_BUCKET` | dashboard | empty | Enables the "Upload report to S3" button (needs AWS credentials) |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DB_PORT` | Docker Compose | `attention` / `attention` / `attentiondb` / `5433` | Local database settings |

[.env.example](.env.example) lists them all. Docker Compose reads `.env` automatically; the client, dashboard and
scripts read ordinary environment variables.

## How the score works

For each frame, MediaPipe returns 478 face landmarks. The client then computes:

1. **Eye Aspect Ratio (EAR)** for each eye from six landmarks: `(|p2-p6| + |p3-p5|) / (2 * |p1-p4|)`.
   It falls toward 0 as the eye closes. The two eyes are averaged.
2. **Eye score** = `clamp(EAR / your_baseline_EAR * 100, 0, 100)`, so your own normal open eyes score 100 and
   half-closed eyes score about 50. The baseline is measured during calibration (the median over about 90
   frames, so blinks do not skew it). With `CALIBRATE=0` it falls back to `clamp(EAR * 250, 0, 100)`.
3. **Head score** = 100 if the head is roughly facing the screen, 40 if turned away (see limitations).
   Calibration also records where your nose sits when you face the screen, and head direction is measured
   from that point, so sitting off-centre does not matter.
4. **Raw score** = `0.7 * eye score + 0.3 * head score`, then a moving average over the last 5 frames.

The scoring code lives in [client/scoring.py](client/scoring.py) as plain functions, with unit tests in
[client/tests](client/tests).

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/attention` | Store one reading (201). Fields: `session_id`, `student_id`, `timestamp` (Unix seconds), `attention_score` (0-100), `ear` (0-1), `yaw`, `pitch`, `roll` |
| `GET` | `/attention?student_id=&limit=` | Latest readings, newest first |
| `GET` | `/health` | Liveness and database check |

Interactive documentation is served at `/docs`.

![API documentation](docs/images/api-docs.jpg)

## Project structure

```
client/         Webcam client (MediaPipe + scoring) and its tests
backend/        FastAPI service, SQLAlchemy model, tests, Dockerfile
dashboard/      Streamlit app, data layer, tests, Dockerfile
scripts/        db_check.py, seed_demo_data.py
infra/terraform AWS infrastructure (VPC, EC2, RDS, S3, IAM, SSM)
docs/           Deployment guide, privacy notes, images
docker-compose.yml       Local stack (db + backend + dashboard)
docker-compose.aws.yml   Stack used on the EC2 host
```

## Development

```bash
# per component: backend, client, dashboard
cd backend && pip install -r requirements-dev.txt && pytest -q tests

# lint (from the repo root)
pip install ruff && ruff check .
```

## Deploying to AWS

The first version of this project ran on AWS (EC2, RDS PostgreSQL, S3). That deployment is no longer running;
the infrastructure is now defined in [infra/terraform](infra/terraform) so it can be recreated, and torn down
again, with `terraform apply` / `terraform destroy`. Step-by-step instructions, the cost estimate and the
security notes are in [docs/deployment.md](docs/deployment.md).

## Privacy and responsible use

- Frames are processed in memory on the student's computer and are never stored or transmitted.
- What leaves the machine: student ID, session ID, timestamp, attention score, EAR and a head-direction value.
- Monitoring people requires informed consent. Tell students what is measured and why, and follow your
  institution's policy and local law.
- The score is a rough heuristic and has not been validated. It should not be used for grading, discipline or
  any other high-stakes decision.

More detail in [docs/privacy.md](docs/privacy.md).

## Known limitations and roadmap

- **Head direction is a proxy.** "Yaw" is the nose position relative to your calibrated neutral point, not true
  head rotation, so it can also change if you shift sideways without turning. `pitch` and `roll` are sent as 0.
  Proper head-pose estimation (`solvePnP`) is the next scoring improvement.
- **Calibration is per session and assumes you calibrate while attentive.** If your eyes are half closed or you are
  looking away during those 3 seconds, the baseline will be off. Press `c` to redo it.
- **A student who leaves the frame produces a gap, not a low score.**
- **AWS deployment has no HTTPS** and the dashboard has no login (it is IP-restricted). See the deployment guide.
- The Terraform has been validated but not applied by CI.

## License

[MIT](LICENSE)
