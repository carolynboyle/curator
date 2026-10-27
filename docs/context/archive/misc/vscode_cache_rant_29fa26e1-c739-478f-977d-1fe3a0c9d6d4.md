# Gaslighting-as-a-Feature: The Feature That Saves You and the Bug That Gaslights You Are the Same Line of Code

*Notes from a debugging session, for whenever the dev.to post happens.*

## The symptom

Working through a series of markdown changedocs with Claude — each one
superseding the last as mistakes got caught and fixed. Same filename each
time, deliberately: `CHANGEDOC_WIRE_DETAIL_FETCH_TO_API.md`, deleted and
recreated on disk rather than renamed, to avoid a graveyard of
`_v2`/`_v3`/`_final_FINAL` files.

Third time downloading the revised file. Definitely not open in an editor
tab — closed it before the file was even replaced on disk. Opened it
again in VS Code.

It showed the **old** content. Not "slightly out of sync" old — showing
a version with a bug already confirmed fixed, with the corrected version
sitting right there in a browser tab for direct comparison.

## What it actually was

VS Code (like a lot of editors) caches file content by something more
persistent than "the path you typed" — plausibly the tab's file handle,
plausibly its own content cache, plausibly something in how it indexes a
delete-then-recreate at the same path. A plain edit-and-save is fine;
VS Code watches the file and reloads. A delete-and-recreate at an
identical path is apparently a different case, and not always one it
notices — even, per this session, when the tab was already closed before
the replacement happened.

## The part that makes it funny instead of just infuriating

This exact caching behavior is *also* the reason a crashed system doesn't
lose your open tabs — VS Code remembers what was open and restores it,
content and all, on next launch. That's genuinely good. That's the
feature working as intended.

It is, near as anyone can tell, **the same underlying mechanism** that
just spent several minutes making a fully sane person question whether
they were losing their mind. From the inside, "helpful crash recovery"
and "stubbornly gaslighting you about a file you definitely replaced" are
indistinguishable until you've already burned the time figuring out which
one you're looking at.

## The workaround

Close the whole editor. Not the file — the application. Reopen it fresh.

No amount of closing-and-reopening the tab, or the folder, or trusting
that "I definitely closed this before I touched the file" fixed it. Full
cold restart, every time a changedoc got revised under the same filename.

Renaming every revision (`_v2`, `_v3`) would dodge the bug, but trades a
five-second annoyance for a much worse one — a pile of near-identical
filenames with no clear "which one is current" answer, which is a worse
failure mode than the caching bug it avoids.

## The actual point, for anyone newer to a tool or a stack

For a few minutes, the instinct was "I must be doing something wrong" —
not "this tool is doing something wrong." That instinct isn't dumb, it's
just what happens when you don't yet have enough scar tissue with a
specific tool to instantly tell "I made an error" apart from "the tool
did something objectively unreasonable." Experienced users hit the exact
same VS Code behavior and think "ugh, cache, cold restart" in under a
second — not because they're smarter about it, but because they've
already spent the confusion budget on this specific bug once before and
filed it away.

When you're new to a stack, every friction point is ambiguous by
default. You don't have the backlog of "oh, THAT again" to draw on yet.
That ambiguity is the actual cost of being new — not a character flaw,
not a knowledge gap you're behind on. Just a rep count you haven't hit.

## Round two, which makes it worse, not better

Cold restart done. This time: open VS Code in an empty parent folder,
then navigate down into the actual project from inside the editor —
a different action entirely from "reopen the same directory." Should be
about as clean a slate as exists.

The changedoc tab was open again anyway.

This time the content was correct — the version downloaded three times
over, the one that actually matched disk. Which sounds like good news,
except it means the failure mode isn't "VS Code shows stale content,"
it's "VS Code will restore *some* tab state across an action that looks
nothing like session recovery, and whether what it shows you is right or
wrong is not something you can know in advance." A bug with a consistent
symptom is annoying but at least legible — you learn the pattern and
route around it. A bug that's sometimes silently correct is the one that
actually erodes trust, because now every open tab carries a "is this
real" tax, indefinitely, with no reliable signal for when to pay it.

## The tell, if you're stuck in that ambiguity right now

If a file's content looks wrong in a way that doesn't match what you just
did, and closing-the-tab/reopening-the-tab doesn't fix it — stop trusting
the editor specifically, not the file. Compare against a second source
(browser preview, `cat` in a terminal, anything that isn't the same
editor instance) before assuming you broke something. If the second
source agrees with what you expected and the editor doesn't, it's the
editor. Cold restart it and move on — it's not a reflection of anything
you did wrong.

---

*Working title candidates: "VS Code's Cache Doesn't Know the Difference
Between Saving Your Life and Ruining Your Morning" / "The Broligarchs'
Plot to Take Over the World By Driving Us All Mad, Episode 1: My Text
Editor"*
