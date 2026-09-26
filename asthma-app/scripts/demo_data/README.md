# Demo calendar data

## `lobelia_college_jul_aug_2026.ics`

Throwaway demo schedule for a fictional college student (**Jul–Aug 2026**, America/Chicago):

- Weekday lectures / lab / gym / study group  
- Thursday outdoor soccer (good Copilot pollen demo)  
- Weekend outdoor walks / trail runs  
- One-offs: July 4 picnic, midterms, move-in, club fair  

### Use with a throwaway Gmail

1. Create any Gmail you control (e.g. a new account — `lobelia@gmail.com` is only a label here; that address may already be taken).
2. In Google Calendar: **Settings → Import & export → Import** → choose this `.ics`.
3. In Mirror Lake: sign in as your app user → **Connect Google Calendar** with that Gmail (OAuth client must allow the redirect URI from `docs/CALENDAR.md`).

Google will only return events for the window the API requests (e.g. tomorrow for forecast). Importing a full month still helps when you change the forecast date or browse events in Calendar.
