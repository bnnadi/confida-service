# Rollback Last Execution

## Trigger
Command: `/rollback [--confirm]`

## Description
When triggered, I will:
- Identify the last change applied using `/execute` (or `/execute --confirm`).  

- If run as `/rollback`:  
  - Immediately revert those changes across all affected files.  
  - Restore the codebase to the state before the last execution.  
  - Run a type check and linting pass to confirm nothing broke.  

- If run as `/rollback --confirm`:  
  - Generate a **diff preview** of what will be undone.  
  - Wait for your approval before reverting.  
  - Only after confirmation, rollback the changes.  

## Output
- `/rollback`: Summary of reverted files + confirmation of successful rollback.  
- `/rollback --confirm`: Diff preview → then rollback (if approved).  

## Examples
- `/rollback` → instantly undo last `/execute` change.  
- `/rollback --confirm` → preview the rollback diff, then undo after approval.  