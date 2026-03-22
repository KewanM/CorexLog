# CortexLog

CortexLog is a modular Python CLI assistant that turns free-form text into structured notes, tasks, and events using the OpenAI API. The system stores extracted items in SQLite and preserves both the original input and the AI JSON response in `raw_logs` for future analysis.

## Architecture

The application follows a layered architecture:

User -> CLI -> AI Processor -> JSON -> Services -> Database -> SQLite

For read flows:

User -> CLI -> Services -> Database -> CLI Output

Responsibilities are separated across:

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
├── cortexlog/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

Application code remains in the `cortexlog/` package:

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
python -m cortexlog.main write "Tomorrow call John at 3pm and finish the report"
python -m cortexlog.main tasks
python -m cortexlog.main today
python -m cortexlog.main notes
```

## Data Storage

- SQLite database file: `cortexlog.db`
- Log file: `cortexlog.log`
- Raw AI input/output audit table: `raw_logs`

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

## CI Pipeline

GitHub Actions runs on:

- every push to `main`
- every Pull Request targeting `main`

The workflow:

- installs Python 3.11
- installs dependencies
- runs `flake8 .`
- runs `pytest`
- builds the project with `python -m build`

## Branch Protection

Enable these GitHub branch protection rules for `main`:

- Require a pull request before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Require at least one review before merging

## Notes

- The CLI initializes the database automatically before each command.
- Both the user's raw text and the validated AI JSON are always stored in `raw_logs`.
- `today` shows open tasks due today and events scheduled today.
