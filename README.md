# Wizard World Exhibition — hosting guide

This repository runs the exhibition website in two places:

| Server | What it hosts | Files it uses |
|---|---|---|
| **GitHub Pages** | The web page people open | `docs/index.html` |
| **Vercel** | The Python "brain" that runs the simulation and reads the Wizard World API | `app.py`, `requirements.txt`, `wizard_analytics.py` |

Both are deployed from this one GitHub repository. `README.md` is just this guide.

---

## Part A — Put the files on GitHub

1. Go to **github.com** and sign in (or sign up).
2. Click **+** (top right) → **New repository**.
   - Repository name: `wizard-exhibition`
   - Choose **Public** (GitHub Pages is free for public repositories)
   - Leave "Add a README file" **unchecked**
   - Click **Create repository**
3. On the new, empty repository page, click the link **uploading an existing file**.
4. In File Explorer, open the `deploy` folder inside your Exhibition Template folder.
   Select **everything inside it**: `docs` (folder), `app.py`, `requirements.txt`,
   `wizard_analytics.py`, `README.md`. Drag them all into the browser window.
5. Wait until the list shows every file, including `docs/index.html`, then click
   **Commit changes**.
6. Check that the repository now shows: `docs`, `README.md`, `app.py`,
   `requirements.txt`, `wizard_analytics.py`.

## Part B — Put the Python server on Vercel

7. Go to **vercel.com** → **Sign Up** → choose **Hobby** → **Continue with GitHub**,
   and allow access when GitHub asks.
8. Click **Add New…** → **Project**.
9. Find `wizard-exhibition` in the list and click **Import**.
   If it is not listed, click **Adjust GitHub App Permissions** and give Vercel
   access to that repository.
10. On the configure screen, **don't change anything**. Framework Preset should
    read **Flask** and Root Directory `./`. Click **Deploy**.
11. Wait for it to finish (1–3 minutes; it is installing numpy and numba).
12. Copy your Vercel address from the project page under **Domains**. It looks
    like `https://wizard-exhibition.vercel.app` (sometimes with extra letters).
13. Test it: open `https://YOUR-ADDRESS.vercel.app/api/config`. You should see a
    page of text data. The first visit can take up to a minute.

## Part C — Tell the page where the server is

14. On GitHub, open `docs` → `index.html` → click the **pencil icon** (Edit).
15. Press **Ctrl+F** and search for `PASTE-YOUR`. You'll find this line:

    ```js
    const API_SERVER = "https://PASTE-YOUR-VERCEL-ADDRESS.vercel.app";
    ```

    Replace the address inside the quotes with yours from step 12.
    Keep the quotes, and don't put a `/` at the end:

    ```js
    const API_SERVER = "https://wizard-exhibition.vercel.app";
    ```

16. Click **Commit changes…** → **Commit changes**.

## Part D — Turn on GitHub Pages

17. In the repository, click **Settings** → **Pages** (left sidebar).
18. Under **Build and deployment**, set **Source: Deploy from a branch**, then
    **Branch: `main`** and folder **`/docs`**. Click **Save**.
19. Wait 1–2 minutes and refresh. The top of the page will say
    **"Your site is live at https://YOUR-USERNAME.github.io/wizard-exhibition/"**.
20. Open that link. **That link is the one you turn in.**

---

## What to expect

- **First visit after it has been idle:** the page shows *"Waking the Python
  server…"* for up to a minute, then the room appears. That's the free Vercel
  server starting up and compiling the simulation.
- **The room restarts** from its starting conditions after a wake-up.
- **"Write JSON to exports/"** doesn't work online, because the server can't keep
  files. Run `python app.py` on your own computer for Grasshopper exports.
- The page stops asking the server for updates when its tab is hidden, which
  saves your free Vercel usage.

## Making changes later

Edit a file on GitHub (pencil icon) or upload a replacement. Both GitHub Pages
and Vercel redeploy by themselves within a couple of minutes.

## If something goes wrong

- **"This page has not been linked to its Vercel server yet"** → Part C wasn't
  done, or the address has a typo.
- **Stuck on "Waking the Python server…" for more than 2 minutes** → open
  `https://YOUR-ADDRESS.vercel.app/api/config` directly. If it shows an error, go
  to Vercel → your project → **Logs**, and copy the error into Claude.
- **Vercel deploy failed** → open the failed deployment → **Build Logs**, and copy
  the red error lines into Claude.
