1. Phase 1: Review & Understanding
Review the requirements in the file requirements.md first
    - Analyze by broken down sub-sections inside this requirements.txt file (e.g.: section A, section B, etc)
    - Summarize what you understand about these sections. e.g.: what are requirements, scenario of this product requirement, product requirements, cubic metrisc for evaluation, deliverables, etc.
    - Return your understanding to me and ask me if you understand the requirements correctly as expected
    - When I confirm that you understand correctly or stuff like this, you should go ahead otherwise, please remind me to review your understanding to continue or else just hanging there

2. Phase 2: Planning
After reviewing, going to planning phase. I will ask you to give me the detail plan with all necessary phases:
- Summarized all Requirements
- Strategic planning
- Architecture
- Code Structure, API design and other helpful stuff for this step

3. Phase 3: Implementation
When I complete reviewing and confirm you to execute the plan, it's time to implement otherwise remind me or don't implement
Implementation:
- Explain and provide step-by-step details of each directory and each file what you want to do and comment for important ambiguity or info
- Add/update files
- Always have tests for the logic
- Add the evaluate mechanism or model about how to evaluate the response return back by the agent

4. Phase 4: Instruction:
Instruction:
- Provide README.md
- Provide ARCHITECTURE.md
- Provide other .md file and/or instruction files to show step-by-step of how to provision the app, evaluate the model/product/output, how to fine-tune them, demo script to run in one file (Makefile/bash, but Makefile the best) recap metrics if any and relevant stuff at this step

5. You can recommend other phase if you see it makes sense

** RULE TO REMEMBER
1. Do phases sequentially, phase 1 > phase 2 > phase 3 > phase 4 > recommended phase by you - Cursor
2. At Phase 1: review and summarize all your understanding at once
3. At Phase 2: Planning, you can provide me all the planning at once but in sequence, meaningful and structural (having title, description for each sub-section or bullet point, then your suggestion, etc)
4. At Phase 3: please DO NOT implement all at once, Please do them one by one with my approval before coming to next one. And do them with direction of top-down approach, can be: high priority to lower priority, or general to detail, or whatever you think it makes sense; but ONE-BY-ONE of each step in implemetation
    For ex: implement one file per action, I review and approval so you can continue to implement the next action
5. At Phase 4: follow the practical industry to write down the README.md, ARCHITECTURE.md, instruction files, etc to be:
- Concise
- Helpful
- Simple but meaningful
- Understandable
- Attractive (can add more photo to be attractive)
- Other criteria you think it makes sense
6. What makes you confused: my prompt, your understanding, etc., please feel free to ask me again to be more clarified.
7. This project is built specific agentic application that can get client's requirements especially gennerating video from their prompts, so please build this product as an agentic ai application and must have a mechanism to evaluate and fine-tune the output return back from service, having clear metrics/criteria to evaluate them and reason again to optimize the output following the best practice in the market


***
Where the plan lives
By default, Cursor saves plans under your home directory:

~/.cursor/plans/<name>.plan.md
(e.g. on your machine: chemistry_video_challenge_guide_515cbb24.plan.md)
That’s global, not tied to one repo until you save it into the project.

To keep it with your project, use “Save to workspace” in the plan UI. It moves/copies into:

cursor_project/.cursor/plans/<name>.plan.md
Then it’s versioned with the repo and easier to find next time.

How to modify the plan multiple times
You have three good options — you can mix them:

1. Edit the markdown yourself
Open the .plan.md file, change steps, remove tasks, add constraints, then tell the agent in the same Plan-mode chat:

“Update the plan to match my edits in …plan.md”
or
“Revise steps 3–5: use FastAPI job store, no SQLite yet.”

Stay in Plan mode until you’re happy. Don’t click Build until then.

2. Ask in chat (stay in Plan mode)
Keep the same Plan conversation and send follow-ups, for example:

“Drop phase 2; merge into phase 1.”
“Add error handling for failed TTS.”
“Use ai_agent_chemistry/ only, not claude/.”
The agent can update the same plan file (Cursor’s plan tools are built for create/update). Each round refines the plan; you still only Build when ready.

3. Save to workspace, then iterate in Agent (optional)
If you already saved to .cursor/plans/:

Open that file in the editor.
In Agent mode (not Plan), you can say:
@.cursor/plans/my-feature.plan.md update this plan: …
That’s handy for small edits when you’re not in Plan mode anymore.
For big design changes, Plan mode + same thread is usually cleaner.

Suggested workflow
Plan mode → first plan
    ↓
You edit .plan.md and/or ask for revisions (repeat 2–5×)
    ↓
“Save to workspace” (once you like the direction)
    ↓
Final review → Build
If Build already ran and the result is wrong, Cursor recommends: Revert the code changes → refine the same plan → Build again (faster than fixing in Agent mid-flight).

Practical tips
Do	Why
Stay in one Plan chat for revisions
Context stays on one plan file
Use Save to workspace early
Plan lives in the repo, not only ~/Admin/.cursor
Reference the file with @.cursor/plans/...
Agent knows exactly which plan to update
Avoid Build until the plan is final
Build = start coding
There isn’t a separate “plan revision counter”; each message in Plan mode can update the same .plan.md until you approve Build.

If you want, paste the path of your current plan.md (or its name under ~/.cursor/plans/) and we can walk through a concrete 2–3 round revision flow for your chemistry video project.
***