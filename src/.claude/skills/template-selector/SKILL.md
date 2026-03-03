---
name: template-selector
description: Selects a suitable project template from the examples directory and copies it to a specified destination.
license: MIT
---

# Template Selector

## Description
This skill automates the process of initializing a new project by selecting an appropriate template from the `examples` directory. It matches a keyword (e.g., "react", "vue", "nextjs") to the available templates such as `reactjs-template`, `vue-template`, etc., and copies the project structure to a target destination.

Use this skill when the user asks to:
- "Start a new React project"
- "Create a Next.js app in directory X"
- "Initialize a project using the clerk starter"
- "The name of the project template does not need to match exactly; it just needs to meet the requirements in terms of framework and functionality."

## Usage

Run the helper script with a keyword and a destination path. 

```bash
python scripts/helper.py <keyword> <destination_path>
```

## Examples

### Check Available Templates
To see a full list of available templates and their descriptions, please refer to [reference.md](reference.md). You can use this file to help the user choose the best template for their needs.

### Initialize a React project
If the user says "Create a React app in ./my-new-app":

```bash
python scripts/helper.py "react" "./my-new-app"
```

### Initialize a Next.js project
If the user says "I need a nextjs template":

```bash
python scripts/helper.py "nextjs" "./next-app"
```

### Using a specific starter
If the user asks for "clerk authentication":

```bash
python scripts/helper.py "clerk" "./clerk-demo"
```
