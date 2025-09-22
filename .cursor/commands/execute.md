# Execute Suggestion

## Trigger
Command: `/execute [--confirm]`

## Description
When triggered, I will:
- Take the **most recent suggestion or fix from the chat context** (from code review, tickets, or explanation).  
- If run as `/execute`:  
  - Apply the change directly to the codebase.  
  - Ensure project conventions (TypeScript typings, linting, formatting) are followed.  
  - Run a quick type check to confirm no errors introduced.  
- If run as `/execute --confirm`:  
  - Generate a **diff preview** of the proposed changes.  
  - Wait for your approval before applying.  
  - Only after confirmation, update the codebase.  

## Output
- `/execute`: Updated codebase + summary of changed files.  
- `/execute --confirm`: Diff preview → then updated codebase (if approved).  

## Examples
- `/execute` → immediately applies last chat suggestion.  
- `/execute --confirm` → shows a diff preview first, then applies after approval.  