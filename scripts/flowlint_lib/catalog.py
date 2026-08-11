"""Findings catalogue: the human-facing text for every rule.

A finding is only useful if the reader can act on it without opening the code
first. So every rule carries four things:

    what   -- what the code actually does (mechanical, verifiable)
    impact -- what the user experiences because of it (concrete, not abstract)
    fix    -- what to change, phrased for the stack in question
    effort -- rough size, so the reader can triage

`{...}` placeholders are filled from the node at report time.
"""

# effort: S = under an hour, M = half a day, L = needs a design decision
# confidence: certain = the graph proves it; likely = strong signal, verify

CATALOG = {
    # ------------------------------------------------------------ structural
    "deadend": {
        "title": "Dead end: there is no way out of this screen",
        "severity": "high", "confidence": "certain", "effort": "M",
        "what": "Nothing leaves “{label}”. The flow stops here, and this is not a "
                "goal node.",
        "impact": "When a user reaches this point the app abandons them. Their only "
                  "remaining option is to close the tab or kill the app. This is "
                  "where sessions end.",
        "fix": "Give this screen at least one way forward: complete, retry, or a safe "
               "exit back to somewhere useful. Ask why a user arrives here and offer "
               "the action that follows from it.",
    },
    "only_exit_is_back": {
        "title": "The only way out is backwards",
        "severity": "high", "confidence": "certain", "effort": "M",
        "what": "The only transition leaving “{label}” is a back or cancel action. "
                "Nothing moves the user forward.",
        "impact": "The user reaches this screen but cannot make progress from it. "
                  "Either the screen is in the wrong place, or the path that completes "
                  "it was never built.",
        "fix": "Decide what this screen is for. If it informs, give it a continue "
               "action; if it is an intermediate step, connect it to the next one.",
    },
    "unreachable": {
        "title": "Unreachable screen",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "No path from any entry point reaches “{label}”.",
        "impact": "Either this is dead code — maintenance weight and confusion — or a "
                  "transition that led here was removed or broken. In the second case "
                  "users have lost access to something they need.",
        "fix": "Delete it if it is dead. If it should be reachable, restore the missing "
               "transition. If it is only ever opened by a deep link, model that link "
               "as a `start` node.",
    },
    "orphan": {
        "title": "Nothing links here — reachable only by deep link",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "No transition inside this flow leads to “{label}”.",
        "impact": "A user can only land here from a link they already hold. They will "
                  "not find it by navigating the app.",
        "fix": "If that is intentional (an email link, a notification target), model it "
               "as a `start` node and say so. If not, give it an entry point people can "
               "actually find.",
    },

    # ------------------------------------------------------------ error paths
    "no_error_branch": {
        "title": "Network call with no failure branch",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "“{label}” is a network call, but no transition models what happens "
                "when it fails.",
        "impact": "When the request fails — timeout, 500, offline — it is undefined "
                  "what the user sees. In practice they usually see nothing: the screen "
                  "freezes or silently stays empty. Not knowing what happened, they try "
                  "again, and again.",
        "fix": "Catch the rejection and show it: a message plus a way to retry. Treat "
               "timeouts separately — a request that never returns is also a failure.",
    },
    "external_no_return": {
        "title": "No cancel or failure path back from an external service",
        "severity": "high", "confidence": "likely", "effort": "M",
        "what": "“{label}” hands the user off to another site, but only the success "
                "return is modelled. There is no transition for a cancellation or an "
                "error coming back.",
        "impact": "If the user presses Cancel on the external screen — an OAuth consent "
                  "page, 3-D Secure, a payment provider — or hits an error there, where "
                  "they land is undefined. Typically they arrive back at the start with "
                  "no explanation and no idea what went wrong.",
        "fix": "Read the provider's cancel and error parameters (`error`, "
               "`error_description`, `denied`) and route to a state that tells the user "
               "what happened. Design the return URL to carry that information.",
    },
    "redirect_loop": {
        "title": "Possible redirect loop",
        "severity": "high", "confidence": "likely", "effort": "M",
        "what": "These nodes form a cycle with no step in it that can change the user's "
                "situation: {cycle}.",
        "impact": "If the underlying error persists — a session that keeps being "
                  "rejected, say — the user is stuck in the loop: screens flick past, "
                  "nothing ever advances. This is the most common reason an app feels "
                  "“frozen”.",
        "fix": "Add a counter or a break condition. After N attempts, show a screen "
               "that explains what is happening and offers an alternative.",
    },
    "waiting_no_resend": {
        "title": "Waiting on something out of band, with no way to resend",
        "severity": "high", "confidence": "likely", "effort": "S",
        "what": "At “{label}” the user is waiting for something delivered outside the "
                "app — an emailed link, an SMS code — and this screen offers no way to "
                "resend it or switch method.",
        "impact": "If the email lands in spam or the SMS never arrives, the user is "
                  "locked out completely. Their only option is to start over, and most "
                  "people do not: they leave.",
        "fix": "Add a resend action with a cool-down, and offer an alternative method. "
               "Show where it was sent, too, so a mistyped address is visible.",
    },
    "decision_single_branch": {
        "title": "Decision point with only one branch",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "“{label}” is a decision, but only one path leaves it.",
        "impact": "Either the alternative branch is missing from the map, or it is "
                  "missing from the code — in which case the user goes nowhere when "
                  "the condition is not met.",
        "fix": "Check the `if`/`else` in the code. If there is no else branch, add one; "
               "if there is, model it.",
    },

    # ------------------------------------------------------------ friction
    "friction:no_error_state": {
        "title": "The error is never shown to the user",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "There is a failure path for “{label}”, but nothing in the interface "
                "surfaces it.",
        "impact": "When something goes wrong the user cannot tell. They are left with a "
                  "blank or unchanged screen, repeat the same action, and get the same "
                  "result. This is the most common cause of silent abandonment.",
        "fix": "Wire the error state into the UI. When the error travels by redirect "
               "(`?error=...`), make sure the destination page actually reads that "
               "parameter — this step is skipped surprisingly often.",
    },
    "friction:silent_failure": {
        "title": "The error is swallowed",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "The catch block in “{label}” only logs. Nothing changes in the "
                "interface.",
        "impact": "The user never learns the operation failed. Worse, they may believe "
                  "it succeeded. This is the class of bug that produces lost data and "
                  "support tickets.",
        "fix": "Produce a visible result in the catch block. A log is not enough — the "
               "user does not read your logs.",
    },
    "friction:no_loading_state": {
        "title": "No pending state while waiting",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "“{label}” starts an asynchronous operation with no indication that "
                "anything is happening.",
        "impact": "The user cannot tell whether their tap registered, so they tap "
                  "again — which is how you get double submissions, double charges and "
                  "duplicate records.",
        "fix": "Disable the control and show progress (a spinner, a skeleton) for the "
               "duration. Guard against double submission on the server as well.",
    },
    "friction:no_empty_state": {
        "title": "No empty state",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "“{label}” renders a list but does not define what appears when the "
                "list is empty.",
        "impact": "A new user opens it and sees a blank screen, and concludes the app "
                  "is broken. This is where first impressions are most often lost.",
        "fix": "Write the empty state: explain what belongs here and offer the action "
               "that creates the first item.",
    },
    "friction:no_back_affordance": {
        "title": "No way back",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "“{label}” offers no way back — the back control is hidden, the gesture "
                "is disabled, or the stack has been cleared.",
        "impact": "A user who opens this screen by mistake is trapped in it. On mobile "
                  "that ends with the app being force-closed. It is the moment a person "
                  "stops feeling in control.",
        "fix": "Provide a back or cancel action. If clearing the stack is deliberate "
               "(after a payment, say), at least give an explicit way to finish.",
    },
    "friction:forced_signup": {
        "title": "Sign-up required where it need not be",
        "severity": "high", "confidence": "likely", "effort": "L",
        "what": "“{label}” requires an account, although the service behind it can "
                "serve a guest.",
        "impact": "The user is asked to commit before seeing any value. This is the "
                  "most expensive step in a funnel; measured drop-off is usually "
                  "highest right here.",
        "fix": "Offer a guest path. Move account creation to *after* the action and "
               "pre-fill it with what you already collected.",
    },
    "friction:long_form": {
        "title": "Long form",
        "severity": "medium", "confidence": "certain", "effort": "M",
        "what": "“{label}” has more than five required fields on one screen.",
        "impact": "Every required field is another chance to give up. Long forms have "
                  "markedly higher abandonment, especially on mobile.",
        "fix": "Separate what is genuinely required. Defer or make optional the rest, "
               "and pre-fill anything you can infer — location, country, last order.",
    },
    "friction:duplicate_input": {
        "title": "Asks again for data you already have",
        "severity": "medium", "confidence": "likely", "effort": "S",
        "what": "“{label}” asks for information the app collected earlier in this flow.",
        "impact": "The user thinks “I just typed this.” The sense that the app does not "
                  "remember them erodes trust in everything else it does.",
        "fix": "Carry it over from the earlier step and pre-fill the field, leaving it "
               "editable.",
    },
    "friction:blocking_modal": {
        "title": "Blocking modal",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "“{label}” opens a layer over the flow that cannot be dismissed.",
        "impact": "The user is pulled away from what they were doing and cannot get "
                  "back. On a critical path this is a direct loss of conversion.",
        "fix": "Add a way out — Escape, click-outside, a close button. Better still, do "
               "not show it over a critical flow; move it to after the task.",
    },
    "friction:unskippable": {
        "title": "Interstitial that cannot be skipped",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "“{label}” is an intermediate step with no way past it.",
        "impact": "A user who knows what they came for is slowed down. On repeat visits "
                  "the annoyance compounds.",
        "fix": "Add a skip action, or show it only on first run.",
    },
    "friction:destructive_no_confirm": {
        "title": "Irreversible action with no confirmation",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "“{label}” performs an irreversible action with no confirmation step "
                "before it.",
        "impact": "One mistaken tap destroys data. There is no recourse for the user, "
                  "and an expensive one for your support team.",
        "fix": "Add a confirmation — or better, make it undoable: soft-delete plus an "
               "“undo” notification.",
    },
    "friction:hidden_cta": {
        "title": "Primary action below the fold",
        "severity": "medium", "confidence": "likely", "effort": "S",
        "what": "The primary action on “{label}” requires scrolling to reach.",
        "impact": "The user cannot see what to do next. On small screens the flow "
                  "simply stops here.",
        "fix": "Pin the primary action to a fixed bar, or shorten the content so it "
               "fits above the fold.",
    },
    "friction:permission_prompt": {
        "title": "OS permission prompt mid-flow",
        "severity": "medium", "confidence": "certain", "effort": "M",
        "what": "An operating-system permission dialog interrupts “{label}”.",
        "impact": "A permission asked without context is refused at a high rate. And "
                  "when it is refused, how the flow continues has usually not been "
                  "written.",
        "fix": "Explain why the permission is needed before requesting it. **Model and "
               "implement the denial branch** — it is almost always missing.",
    },

    # ------------------------------------------------- flow shape / model quality
    "flow_too_deep": {
        "title": "The primary path is longer than it needs to be",
        "severity": "medium", "confidence": "certain", "effort": "L",
        "what": "The primary path is {steps} steps (threshold {threshold}).",
        "impact": "Every additional step costs users. Long flows complete at "
                  "measurably lower rates, especially on mobile and on first use.",
        "fix": "Look for steps to merge: fields that could share a screen, decisions "
               "that could be deferred, confirmations that could be dropped.",
    },
    "missing_source": {
        "title": "Part of this map cannot be verified",
        "severity": "low", "confidence": "certain", "effort": "S",
        "what": "{count} nodes have no `source` anchor: {names}.",
        "impact": "There is no way to confirm these nodes came from the code. When a "
                  "reader cannot tell which parts are real and which are assumed, they "
                  "trust the whole map less.",
        "fix": "Add the `file:line` each node came from. If this flow describes "
               "something not built yet — a `-proposed` file, for instance — this "
               "finding is expected; accept it with `flowlint ignore` and a reason.",
    },
}

# Tags that describe reality but are not defects. They belong in the diagram and
# in the notes, never in the findings list -- listing them as problems buries the
# real ones.
INFORMATIONAL = {"external_handoff"}

INFO_TEXT = {
    "external_handoff": "At this step the user leaves the app for an external service. "
                        "That is not a problem in itself, but the return paths — "
                        "cancellation and failure — need to be modelled.",
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}
CONFIDENCE_LABEL = {"certain": "certain", "likely": "likely"}
EFFORT_LABEL = {"S": "S (~1 hour)", "M": "M (~half a day)", "L": "L (needs a design decision)"}


def entry(code):
    return CATALOG.get(code)
