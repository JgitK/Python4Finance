# Project documentation

This folder is the lab notebook of the project. Git records what changed.
This folder records why it changed and what the results showed.

| File | What it holds | Who writes it |
|---|---|---|
| [decisions.md](decisions.md) | One entry for each important decision. | You, after each decision. |
| [results_log.md](results_log.md) | One row for each pipeline run. | `run_pipeline.py` adds the row. You write the note. |
| [open_questions.md](open_questions.md) | The problems and questions that are not solved. | You, when you find or solve one. |
| [handoff.md](handoff.md) | The state of the project and the rules of work, for a new chat. | You, at the end of each session. |

## How to use it

1. **Before a change**, read `open_questions.md`. Select one question.
2. **Make the change** in small commits. Write the reason in the body of each
   commit message.
3. **Run the pipeline.** `python run_pipeline.py` adds a row to
   `results_log.md`. Write a short note in the last cell of the new row.
   Use `--no-log` for an experiment that you do not want to record.
4. **After the change**, add an entry to `decisions.md` if you selected one
   option from two or more options. Put the commit hash in the entry.
5. **Update `open_questions.md`.** Move a solved question to the "Solved"
   section with the commit hash.
6. **Commit the documents** with the code, or in the next commit.

## The commit column in the results log

The commit column shows the code that made the row.

- `4cfa116` means that the code was the same as that commit.
- `4cfa116-dirty` means that the code had changes that were not committed.
  Commit the changes, then run the pipeline again to get a clean row.

A run with the same clean commit and the same results does not add a row.
