# CortexLog

CortexLog is a modular Python CLI assistant that turns free-form text into structured notes, tasks, and events using the OpenAI API. The system stores extracted items in SQLite and preserves both the original input and the AI JSON response in `raw_logs` for future analysis.

## Architecture

The application follows a layered architecture:

User -> CLI -> AI Processor -> JSON -> Services -> Database -> SQLite

For read flows:

User -> CLI -> Services -> Database -> CLI Output

Responsibilities are separated across:

- `app/intent_classifier.py`: category detection from title and content
- `app/text_enhancer.py`: rewrite suggestions across enhancement modes
- `app/confirmation_prompt.py`: confirmation gate before anything is saved
- `app/storage_manager.py`: routing entries into structured folders and SQLite
- `app/logger.py`: system action logging
- `cortexlog/cli/commands.py`: Typer CLI commands and output formatting
- `cortexlog/ai/processor.py`: OpenAI integration, JSON parsing, validation, and raw log persistence
- `cortexlog/services/`: business logic for notes, tasks, events, and today views
- `cortexlog/db/`: SQLite connection management and table models
- `cortexlog/utils/`: datetime helpers

## Project Structure

```text
.
├── .github/
│   ├── pull_request_template.md
│   └── workflows/
│       └── ci.yml
├── app/
├── database/
├── cortexlog/
├── logs/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

Application code is split between the `app/` workflow modules and the `cortexlog/` CLI package:

```text
app/
├── confirmation_prompt.py
├── intent_classifier.py
├── logger.py
├── storage_manager.py
└── text_enhancer.py
```

```text
logs/
├── diary/
├── book/
├── tasks/
├── ideas/
├── events/
├── goals/
├── notes/
└── system/
```

```text
database/
└── cortexlog.db
```

Existing CLI and service code remains in the `cortexlog/` package:

```text
cortexlog/
├── main.py
├── cli/
│   └── commands.py
├── ai/
│   └── processor.py
├── db/
│   ├── database.py
│   └── models.py
├── services/
│   ├── notes_service.py
│   ├── tasks_service.py
│   └── events_service.py
├── utils/
│   └── datetime_parser.py
```

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Update `.env` with your OpenAI API key.

## Usage

Initialize and run the CLI with:

```bash
python -m cortexlog.main --help
```

Example commands:

```bash
python -m cortexlog.main write "Today was a hard day at work but I learned a lot" --title diary --mode emotional
python -m cortexlog.main write "Draft a roadmap for the analytics feature" --title idea --mode professional
python -m cortexlog.main tasks
python -m cortexlog.main today
python -m cortexlog.main notes
```

`write` now:

- detects the entry category from the title or text
- generates an enhanced version before saving
- asks for confirmation before saving anything
- supports `professional`, `emotional`, `motivational`, `technical`, and `storytelling` modes
- stores entries in the matching `logs/` folder and in SQLite

## Data Storage

- SQLite database file: `database/cortexlog.db`
- Legacy CLI log file: `cortexlog.log`
- System action log file: `logs/system/system_log.txt`
- Structured writing entries table: `entries`

## AI JSON Contract

The AI processor enforces the following structure before anything is stored:

```json
{
  "notes": [
    {"content": "string"}
  ],
  "tasks": [
    {"content": "string", "due_date": "YYYY-MM-DD HH:MM"}
  ],
  "events": [
    {"title": "string", "event_time": "YYYY-MM-DD HH:MM"}
  ]
}
```

If a task has no due date, `due_date` may be `null`. Empty results use empty arrays.

## Git Workflow

Branch strategy:

- `main`: production-ready code
- `develop`: shared integration branch when the team wants one
- `feature/*`: new features
- `bugfix/*`: bug fixes

Rules:

- Do not commit directly to `main`
- Open a Pull Request for every change
- Merge only after CI passes and review is complete
- Use meaningful conventional-style commit messages such as `feat: add export command`

Developer workflow:

```bash
git checkout -b feature/feature-name
git add .
git commit -m "feat: description"
git push origin feature/feature-name
```

Then open a Pull Request and merge only after CI passes.

SSH setup for GitHub:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
pbcopy < ~/.ssh/id_ed25519.pub
ssh -T git@github.com
git remote set-url origin git@github.com:KewanM/CorexLog.git
```

## CI Pipeline

GitHub Actions runs on:

- every push to `main`
- every push to `develop`
- every Pull Request targeting `main`
- every Pull Request targeting `develop`

The workflow:

- installs Python 3.11
- installs dependencies
- runs `flake8 .`
- runs `pytest`
- runs the build placeholder step

## Branch Protection

Enable these GitHub branch protection rules for `main`:

- Require a pull request before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Require at least one review before merging

## Notes

- `write` never persists anything until the user confirms the save choice.
- Saved entries retain both original and enhanced text in SQLite, with the final save mode recorded.
- Each saved entry is routed into the correct category folder under `logs/`.
- Each save or cancel action is written to `logs/system/system_log.txt`.
- The CLI initializes the database automatically before each command.
- Both the user's raw text and the validated AI JSON are always stored in `raw_logs`.
- `today` shows open tasks due today and events scheduled today.
