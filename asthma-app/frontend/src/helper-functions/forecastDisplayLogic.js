/** Pure display rules for today vs tomorrow predictions (testable without fetch). */

/** True when a forecast payload has a usable advice summary or section body. */
export function forecastHasAdvice(forecast) {
  const advice = forecast?.advice;
  if (!advice || typeof advice !== "object") {
    return false;
  }
  if (String(advice.summary || "").trim()) {
    return true;
  }
  return (
    Array.isArray(advice.sections) &&
    advice.sections.some((section) => String(section?.body || "").trim())
  );
}

export function localYmd(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function yesterdayYmd(now = new Date()) {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  return localYmd(d);
}

export function tomorrowYmd(now = new Date()) {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return localYmd(d);
}

/** Tomorrow's prediction unlocks at 18:00 local time. */
export function isAfterSixPm(now = new Date()) {
  return now.getHours() >= 18;
}

/**
 * Statistics / shared cards: hide tomorrow before 6pm even if stored.
 * @returns {{ today: object|null, tomorrow: object|null }}
 */
export function selectCardPredictions({ today = null, tomorrow = null } = {}, now = new Date()) {
  if (!isAfterSixPm(now)) {
    return { today: today || null, tomorrow: null };
  }
  return { today: today || null, tomorrow: tomorrow || null };
}

/**
 * Home single card: before 6pm → today; after 6pm → tomorrow if present else today.
 */
export function selectHomeForecast({ today = null, tomorrow = null } = {}, now = new Date()) {
  const cards = selectCardPredictions({ today, tomorrow }, now);
  if (isAfterSixPm(now) && cards.tomorrow) {
    return cards.tomorrow;
  }
  return cards.today || cards.tomorrow;
}

/**
 * Home risk heading suffix: TODAY or TOMORROW based on forecast_for.
 * @returns {"TODAY"|"TOMORROW"|null}
 */
export function homeForecastDayLabel(forecast, now = new Date()) {
  if (!forecast?.forecast_for) return null;
  return forecast.forecast_for === localYmd(now) ? "TODAY" : "TOMORROW";
}

/**
 * Home main heading, e.g. "TODAY'S RISK" / "TOMORROW'S RISK".
 */
export function homeRiskHeading(forecast, riskLevel = "Low", now = new Date()) {
  const day = homeForecastDayLabel(forecast, now);
  const level = String(riskLevel || "Low").toUpperCase();
  if (day === "TOMORROW") return `${level} RISK · TOMORROW`;
  if (day === "TODAY") return `${level} RISK · TODAY`;
  return `${level} RISK`;
}

/**
 * Whether Statistics should show the "log today for tomorrow" reminder.
 */
export function statisticsShowTomorrowReminder({
  todayForecast,
  tomorrowForecast,
  todayCheckInComplete,
}, now = new Date()) {
  if (!todayForecast || tomorrowForecast) return false;
  if (isAfterSixPm(now)) return !todayCheckInComplete;
  return true;
}

export function statisticsReminderText({
  todayForecast,
  tomorrowForecast,
  todayCheckInComplete,
}, now = new Date()) {
  if (!statisticsShowTomorrowReminder(
    { todayForecast, tomorrowForecast, todayCheckInComplete },
    now
  )) {
    return null;
  }
  if (todayCheckInComplete && !isAfterSixPm(now)) {
    return "Tomorrow’s prediction will appear here after 6 PM.";
  }
  return "Put in today’s symptoms to get a prediction for tomorrow.";
}
