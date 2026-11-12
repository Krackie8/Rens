# Affiliate income (Shopee MY, Amazon.ae)

Affiliate commissions as one income line in the ORIRI 10k Tracker, target RM300 a month from December 2026.

## The weekly flow

1. **Pick a product you already use** in a post or reel (wellness, desk, planner, beauty).
2. **Make the link** in the Shopee Affiliate or Amazon Associates dashboard, using the tracking ID for that channel.
3. **Add a row to [`links.csv`](links.csv)**: paste the link in `affiliate_url`, note the post in `used_in`, set `active` to `yes`.
4. **Post** with the disclosure line and "link in bio". The bio link goes to the picks page.

Disclosure line for every post with a link:

> Some links are affiliate links; I may earn a small commission at no extra cost to you.

## Picks page

[`index.html`](index.html) reads `links.csv` and shows active links, split into Malaysia (Shopee) and UAE (Amazon.ae) tabs. Once merged it lives at https://krackie8.github.io/Rens/affiliate/ and `?market=UAE` opens the UAE tab, so you can use one Linktree button per country.

## Monthly summary

1. At the start of each month, download last month's report CSV from each dashboard (Shopee: conversion report; Amazon: earnings report).
2. Save them in `affiliate/reports/` with `shopee` or `amazon` in the file name, for example `shopee-2026-12.csv`. This folder is ignored by git, so your earnings never get pushed.
3. Run:

   ```
   python3 affiliate/summarize.py 2026-12
   ```

   It asks for the AED to RM rate if there is Amazon data, then prints clicks, orders, pending and approved commission per platform in RM, plus the line to log in the tracker.

4. Log the approved amount in the tracker as **Expected**. When the payout lands in your bank, mark it **Received**.

The two platforms label their columns differently and change them sometimes. If the script skips a file, it prints the header it saw, so the column names in `summarize.py` can be updated.

## What stays with you

Sign-ups, passwords, tax and bank details are entered by you on the platforms. Nothing here stores credentials or scrapes shop pages.
