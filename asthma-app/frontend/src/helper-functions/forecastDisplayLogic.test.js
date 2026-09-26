import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  forecastHasAdvice,
  homeForecastDayLabel,
  homeRiskHeading,
  isAfterSixPm,
  localYmd,
  selectCardPredictions,
  selectHomeForecast,
  statisticsReminderText,
  tomorrowYmd,
  yesterdayYmd,
} from "./forecastDisplayLogic.js";

function atHour(hour, { y = 2026, m = 7, d = 29 } = {}) {
  return new Date(y, m - 1, d, hour, 0, 0, 0);
}

const todayPred = {
  forecast_for: "2026-07-29",
  flare_probability: 0.59,
  risk_level: "Medium",
};
const tomorrowPred = {
  forecast_for: "2026-07-30",
  flare_probability: 0.5,
  risk_level: "Medium",
};

describe("forecastHasAdvice", () => {
  it("is false when advice is missing or empty", () => {
    assert.equal(forecastHasAdvice(null), false);
    assert.equal(forecastHasAdvice({}), false);
    assert.equal(forecastHasAdvice({ advice: null }), false);
    assert.equal(forecastHasAdvice({ advice: { summary: "", sections: [] } }), false);
  });

  it("is true when summary or section body is present", () => {
    assert.equal(
      forecastHasAdvice({ advice: { summary: "Keep rescue nearby.", sections: [] } }),
      true
    );
    assert.equal(
      forecastHasAdvice({
        advice: {
          summary: "",
          sections: [{ title: "Tonight", body: "Monitor nighttime symptoms." }],
        },
      }),
      true
    );
  });
});

describe("local date helpers", () => {
  it("formats local YMD without UTC shift", () => {
    const evening = atHour(20);
    assert.equal(localYmd(evening), "2026-07-29");
    assert.equal(yesterdayYmd(evening), "2026-07-28");
    assert.equal(tomorrowYmd(evening), "2026-07-30");
  });
});

describe("isAfterSixPm", () => {
  it("is false before 18:00", () => {
    assert.equal(isAfterSixPm(atHour(17)), false);
    assert.equal(isAfterSixPm(atHour(11)), false);
    assert.equal(isAfterSixPm(atHour(0)), false);
  });

  it("is true at and after 18:00", () => {
    assert.equal(isAfterSixPm(atHour(18)), true);
    assert.equal(isAfterSixPm(atHour(18, { d: 29 })), true);
    assert.equal(isAfterSixPm(atHour(23)), true);
  });
});

describe("selectCardPredictions (Statistics)", () => {
  it("hides tomorrow before 6pm even when stored", () => {
    const result = selectCardPredictions(
      { today: todayPred, tomorrow: tomorrowPred },
      atHour(11)
    );
    assert.deepEqual(result, { today: todayPred, tomorrow: null });
  });

  it("shows both after 6pm when both stored", () => {
    const result = selectCardPredictions(
      { today: todayPred, tomorrow: tomorrowPred },
      atHour(19)
    );
    assert.equal(result.today, todayPred);
    assert.equal(result.tomorrow, tomorrowPred);
  });

  it("can show only tomorrow after 6pm", () => {
    const result = selectCardPredictions(
      { today: null, tomorrow: tomorrowPred },
      atHour(20)
    );
    assert.equal(result.today, null);
    assert.equal(result.tomorrow, tomorrowPred);
  });
});

describe("selectHomeForecast (Home)", () => {
  it("shows today's prediction before 6pm (not tomorrow's 50%)", () => {
    const shown = selectHomeForecast(
      { today: todayPred, tomorrow: tomorrowPred },
      atHour(11)
    );
    assert.equal(shown.flare_probability, 0.59);
    assert.equal(shown.forecast_for, "2026-07-29");
  });

  it("shows tomorrow's prediction after 6pm when available", () => {
    const shown = selectHomeForecast(
      { today: todayPred, tomorrow: tomorrowPred },
      atHour(19)
    );
    assert.equal(shown.flare_probability, 0.5);
    assert.equal(shown.forecast_for, "2026-07-30");
  });

  it("falls back to today after 6pm if tomorrow missing", () => {
    const shown = selectHomeForecast(
      { today: todayPred, tomorrow: null },
      atHour(20)
    );
    assert.equal(shown.forecast_for, "2026-07-29");
  });

  it("falls back to tomorrow before 6pm only if today missing", () => {
    // Before 6pm tomorrow is cleared by selectCardPredictions, so result is null.
    const shown = selectHomeForecast(
      { today: null, tomorrow: tomorrowPred },
      atHour(10)
    );
    assert.equal(shown, null);
  });
});

describe("home labels", () => {
  it("labels today vs tomorrow for the home heading", () => {
    const now = atHour(11);
    assert.equal(homeForecastDayLabel(todayPred, now), "TODAY");
    assert.equal(homeForecastDayLabel(tomorrowPred, now), "TOMORROW");
    assert.equal(
      homeRiskHeading(todayPred, "Medium", now),
      "MEDIUM RISK · TODAY"
    );
    assert.equal(
      homeRiskHeading(tomorrowPred, "High", atHour(19)),
      "HIGH RISK · TOMORROW"
    );
  });
});

describe("statistics reminders", () => {
  it("reminds to log today when only today's forecast exists before 6pm", () => {
    const text = statisticsReminderText(
      {
        todayForecast: todayPred,
        tomorrowForecast: null,
        todayCheckInComplete: false,
      },
      atHour(11)
    );
    assert.match(text, /today’s symptoms/i);
  });

  it("says tomorrow unlocks after 6pm when today is already logged", () => {
    const text = statisticsReminderText(
      {
        todayForecast: todayPred,
        tomorrowForecast: null,
        todayCheckInComplete: true,
      },
      atHour(11)
    );
    assert.match(text, /after 6 PM/i);
  });

  it("hides reminder when tomorrow is visible after 6pm", () => {
    const text = statisticsReminderText(
      {
        todayForecast: todayPred,
        tomorrowForecast: tomorrowPred,
        todayCheckInComplete: true,
      },
      atHour(19)
    );
    assert.equal(text, null);
  });

  it("asks to log today after 6pm if tomorrow cannot be shown yet", () => {
    const text = statisticsReminderText(
      {
        todayForecast: todayPred,
        tomorrowForecast: null,
        todayCheckInComplete: false,
      },
      atHour(19)
    );
    assert.match(text, /today’s symptoms/i);
  });
});
