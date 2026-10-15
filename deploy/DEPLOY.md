# Deploying the backend to Cloud Run

Two ways to do it. Start with **Option A** to get the new version live and check that it works. Set up **Option B** afterwards if you want every merge to `main` to deploy by itself.

You don't need to install anything. Both options run in **Google Cloud Shell**, a terminal that opens in your browser (the `>_` button at the top right of https://console.cloud.google.com, with the project `life-saver-c2207` selected).

---

## Option A: deploy by hand (about 10 minutes)

**1. Get the code into Cloud Shell**

```bash
git clone https://github.com/yuv294/Life-saver.git
cd Life-saver
git checkout main          # use the branch name instead if you haven't merged the PR yet
```

**2. Find your existing service name and region**

```bash
gcloud config set project life-saver-c2207
gcloud run services list
```

Note the `SERVICE` and `REGION` columns. Below, replace `MY_SERVICE` and `MY_REGION` with them.

**3. Deploy a test copy that gets no real traffic**

```bash
gcloud run deploy MY_SERVICE --source backend --region MY_REGION --no-traffic --tag candidate
```

- If it asks to enable APIs, answer `y`.
- Your existing environment variables and secrets (Gemini key, database URL, and so on) carry over automatically.
- This builds the new version but keeps your live app on the old one. Nothing breaks if the new one has a problem.
- At the end it prints a URL that starts with `https://candidate---`. That is the test copy.

**4. Check the test copy works**

```bash
curl https://candidate---YOUR-URL/health
```

You should see a short "ok" style reply. Then open your real frontend and try it, or run the measuring script (see "Getting your numbers" below) against the candidate URL.

**5. Send real traffic to the new version**

```bash
gcloud run services update-traffic MY_SERVICE --region MY_REGION --to-latest
```

Changed your mind? In the Cloud Run console, open the service, go to **Revisions**, and send 100% of traffic back to the old revision.

**Optional hardening (do this last)**

```bash
gcloud run services update MY_SERVICE --region MY_REGION --update-env-vars REQUIRE_SECURE_SECRETS=true
```

This makes the app refuse to start if it is still using the default development passwords. If your service starts fine afterwards, your secrets are real. If it won't start, set real values for `SECRET_KEY` and `INTERNAL_API_SECRET` (Cloud Run console > Edit & deploy new revision > Variables & Secrets), or undo with `--remove-env-vars REQUIRE_SECURE_SECRETS`.

---

## Option B: deploy automatically on every merge

1. In Cloud Shell, from the `Life-saver` folder:

   ```bash
   bash deploy/setup_github_deploy.sh life-saver-c2207
   ```

   It takes a minute or two and prints five values at the end.

2. In GitHub open the repo, then **Settings > Secrets and variables > Actions > Variables** and add the five values it printed (`GCP_PROJECT_ID`, `GCP_REGION`, `CLOUD_RUN_SERVICE`, `GCP_SERVICE_ACCOUNT`, `GCP_WORKLOAD_IDENTITY_PROVIDER`). They are IDs, not passwords, so "Variables" is the right tab (not "Secrets").

3. After that, every push to `main` runs the tests, builds the image and deploys it. You can watch it in the **Actions** tab.

There are no passwords or key files in GitHub. Google only trusts runs that come from this exact repo.

If the first automatic deploy fails with a "permission" message, copy the message to me and I'll adjust the roles.

---

## Getting your numbers

Once the service is live you can measure it. From Cloud Shell, inside the `Life-saver` folder:

```bash
python3 backend/scripts/measure_deployed.py --base-url https://YOUR-SERVICE-URL --n 20
```

For the numbers that need you to be signed in, you need a login token. Open your deployed frontend, sign in, open the browser developer tools (F12), go to the **Network** tab, click any request to your API, and copy the value after `Authorization: Bearer `. Then:

```bash
export LIFESAVER_TOKEN="paste-it-here"
python3 backend/scripts/measure_deployed.py --base-url https://YOUR-SERVICE-URL --n 20 --cold
```

The token stops working after about an hour. Don't paste it anywhere public.

Quote only numbers this script prints, and write down the date you measured them.
