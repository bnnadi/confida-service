commands:
  - name: "ReviewCodebase"
    description: "Review the codebase and suggest simplifications, improvements, and refactors."
    prompt: |
      You are an expert software engineer. Review the entire codebase (or the specified files if mentioned). 
      Focus on:
      - Simplifying complex or nested logic
      - Identifying redundant or duplicate code
      - Improving readability and maintainability
      - Suggesting performance optimizations
      Provide:
      - A summary of key improvement areas
      - File-specific recommendations (with line numbers if possible)
      - Suggested simplified code snippets where necessary