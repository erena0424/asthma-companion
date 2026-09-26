import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useCalendar } from "../../context/CalendarContext";
import "./CalendarPage.css";
import CalendarConnectionPanel from "../calendar/CalendarConnectionPanel";
import SpinnerOverlay from "../input/SpinnerOverlay";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const EMPTY_ARRAY = [];

const EMPTY_FORM = {
  daily_day_symp: false,
  daily_night_symp: false,
  daily_limit_activity: false,
  notes: "",
  triggers: "",
  calendar_event: "",
};

function formatDateKey(year, monthIndex, day) {
  const month = String(monthIndex + 1).padStart(2, "0");
  const date = String(day).padStart(2, "0");

  return `${year}-${month}-${date}`;
}

function formatReadableDate(dateKey) {
  const [year, month, day] = dateKey.split("-").map(Number);

  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function CalendarPage() {
  const { token } = useAuth();
  const {
    calendarStatus,
    calendarSnapshot,
    loadCalendarMonth,
    saveCalendarCheckIn,
  } = useCalendar();

  const [currentMonth, setCurrentMonth] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);

  const [error, setError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [saving, setSaving] = useState(false);


  const year = currentMonth.getFullYear();
  const monthIndex = currentMonth.getMonth();

  const monthName = currentMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  const firstDayIndex = new Date(year, monthIndex, 1).getDay();
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

  const monthStart = formatDateKey(year, monthIndex, 1);
  const monthEnd = formatDateKey(year, monthIndex, daysInMonth);
  const monthKey = `${monthStart}:${monthEnd}`;

  const currentMonthData =
    calendarSnapshot.monthKey === monthKey ? calendarSnapshot : null;

  const checkIns = currentMonthData?.checkIns ?? EMPTY_ARRAY;
  const googleEvents = currentMonthData?.googleEvents ?? EMPTY_ARRAY;
  const loading = currentMonthData?.checkInsLoading ?? false;
  const eventsLoading = currentMonthData?.googleEventsLoading ?? false;
  const monthError = currentMonthData?.error ?? "";

  const checkInsByDate = useMemo(() => {
    return Object.fromEntries(
      checkIns.map((checkIn) => [checkIn.date, checkIn])
    );
  }, [checkIns]);

  const googleEventsByDate = useMemo(() => {
    const map = {};
    for (const ev of googleEvents) {
      if (!map[ev.date]) map[ev.date] = [];
      map[ev.date].push(ev);
    }
    return map;
  }, [googleEvents]);

  useEffect(() => {
    if (!token) {
      return;
    }

    void loadCalendarMonth({
      year,
      monthIndex,
      monthStart,
      monthEnd,
      includeEvents: calendarStatus.connected,
      authToken: token,
    });
  }, [calendarStatus.connected, loadCalendarMonth, monthEnd, monthIndex, monthStart, token, year]);


  function goToPreviousMonth() {
    setCurrentMonth(new Date(year, monthIndex - 1, 1));
  }

  function goToNextMonth() {
    setCurrentMonth(new Date(year, monthIndex + 1, 1));
  }

  function openDate(dateKey) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const [selectedYear, selectedMonth, selectedDay] = dateKey
      .split("-")
      .map(Number);

    const selected = new Date(
      selectedYear,
      selectedMonth - 1,
      selectedDay
    );

    selected.setHours(0, 0, 0, 0);

    if (selected > today) {
      setError("You can only record check-ins for today or previous days.");
      return;
    }

    const existingCheckIn = checkInsByDate[dateKey];

    setSelectedDate(dateKey);
    setSaveMessage("");
    setError("");

    if (existingCheckIn) {
      setFormData({
        daily_day_symp: Boolean(existingCheckIn.daily_day_symp),
        daily_night_symp: Boolean(existingCheckIn.daily_night_symp),
        daily_limit_activity: Boolean(
          existingCheckIn.daily_limit_activity
        ),
        notes: existingCheckIn.notes ?? "",
        triggers: Array.isArray(existingCheckIn.triggers)
          ? existingCheckIn.triggers.join(", ")
          : "",
        calendar_event: existingCheckIn.calendar_event ?? "",
      });
    } else {
      setFormData(EMPTY_FORM);
    }
  }

  function closeModal() {
    if (saving) return;

    setSelectedDate(null);
    setSaveMessage("");
  }

  function updateField(event) {
    const { name, value, checked, type } = event.target;

    setFormData((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSave(event) {
    event.preventDefault();

    if (!selectedDate || !token) return;

    const triggers = formData.triggers
      .split(",")
      .map((trigger) => trigger.trim())
      .filter(Boolean);

    try {
      setSaving(true);
      setError("");
      setSaveMessage("");

      const saved = await saveCalendarCheckIn({
        checkIn: {
          date: selectedDate,
          daily_day_symp: formData.daily_day_symp,
          daily_night_symp: formData.daily_night_symp,
          daily_limit_activity: formData.daily_limit_activity,
          notes: formData.notes.trim() || null,
          triggers: triggers.length > 0 ? triggers : null,
          calendar_event: formData.calendar_event.trim() || null,
        },
      });

      if (saved?.forecast_refreshed && saved?.forecast?.risk_level) {
        setSaveMessage(
          `Check-in saved. Risk prediction updated to ${saved.forecast.risk_level}.`
        );
      } else {
        setSaveMessage("Check-in saved.");
      }
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.message || "Unable to save your check-in.");
    } finally {
      setSaving(false);
    }
  }

  const today = new Date();

  const todayKey = formatDateKey(
    today.getFullYear(),
    today.getMonth(),
    today.getDate()
  );

  const calendarCells = [];

  for (let index = 0; index < firstDayIndex; index += 1) {
    calendarCells.push(
      <div
        className="calendar-empty-cell"
        key={`empty-start-${index}`}
        aria-hidden="true"
      />
    );
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateKey = formatDateKey(year, monthIndex, day);
    const hasCheckIn = Boolean(checkInsByDate[dateKey]);
    const hasGoogleEvent = calendarStatus.connected && Boolean(googleEventsByDate[dateKey]);
    const isToday = dateKey === todayKey;

    const dateObject = new Date(year, monthIndex, day);
    dateObject.setHours(0, 0, 0, 0);

    const todayComparison = new Date();
    todayComparison.setHours(0, 0, 0, 0);

    const isFutureDate = dateObject > todayComparison;

    calendarCells.push(
      <button
        type="button"
        className={[
          "calendar-day",
          isToday ? "calendar-day-today" : "",
          hasCheckIn ? "calendar-day-recorded" : "",
          isFutureDate ? "calendar-day-future" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        key={dateKey}
        onClick={() => openDate(dateKey)}
        aria-label={`${formatReadableDate(dateKey)}${
          hasCheckIn ? ", check-in recorded" : ""
        }${isFutureDate ? ", future date unavailable" : ""}`}
        aria-disabled={isFutureDate}
      >
        <span className="calendar-day-number">{day}</span>

        {hasCheckIn && (
          <span
            className="calendar-entry-dot"
            aria-label="Check-in recorded"
          />
        )}
        {hasGoogleEvent && (
          <span
            className="calendar-google-dot"
            aria-label="Google Calendar event"
          />
        )}
      </button>
    );
  }

  function formatEventForSelectedDay(start, end, selectedDate) {
    const startDate = new Date(start);
    const endDate = new Date(end);

    const eventStartKey = startDate.toISOString().slice(0, 10);
    const eventEndKey = endDate.toISOString().slice(0, 10);

    const timeOptions = {
      hour: "numeric",
      minute: "2-digit",
    };

    // Single-day event
    if (eventStartKey === eventEndKey) {
      return `${startDate.toLocaleTimeString([], timeOptions)} – ${endDate.toLocaleTimeString([], timeOptions)}`;
    }

    // First day of a multi-day event
    if (selectedDate === eventStartKey) {
      return `Starts ${startDate.toLocaleTimeString([], timeOptions)}`;
    }

    // Last day of a multi-day event
    if (selectedDate === eventEndKey) {
      return `Ends ${endDate.toLocaleTimeString([], timeOptions)}`;
    }

    // Middle day(s)
    return "All day";
  }

  return (
    <main className="calendar-page">

      <CalendarConnectionPanel />

      <section className="calendar-card">
        <div className="calendar-month-controls">
          <button
            type="button"
            className="calendar-arrow"
            onClick={goToPreviousMonth}
            aria-label="Previous month"
          >
            ←
          </button>

          <h2>{monthName}</h2>

          <button
            type="button"
            className="calendar-arrow"
            onClick={goToNextMonth}
            aria-label="Next month"
          >
            →
          </button>
        </div>

        {loading && <p className="calendar-status">Loading your check-ins...</p>}

        {!loading && monthError && !selectedDate && (
          <p className="calendar-error">{monthError}</p>
        )}

        {!loading && error && !selectedDate && !monthError && (
          <p className="calendar-error">{error}</p>
        )}

        {!loading && (
          <div className="calendar-grid-wrapper">
            <div className="calendar-weekdays">
              {WEEKDAYS.map((weekday) => (
                <div key={weekday} className="calendar-weekday">
                  {weekday}
                </div>
              ))}
            </div>

            <div className="calendar-days-grid">{calendarCells}</div>
          </div>
        )}
      </section>

      {selectedDate && (
        <div
          className="check-in-modal-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeModal();
            }
          }}
        >
          <section
            className="check-in-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="check-in-modal-title"
          >
            <div className="check-in-modal-header">
              <div>
                <p className="check-in-modal-label">Daily check-in</p>

                <h2 id="check-in-modal-title">
                  {formatReadableDate(selectedDate)}
                </h2>
              </div>

              <button
                type="button"
                className="check-in-close"
                onClick={closeModal}
                aria-label="Close check-in"
              >
                ×
              </button>
            </div>

            {calendarStatus.connected && googleEventsByDate[selectedDate] && (
              <div className="card dark-theme mt-3" style={{gap: "16px"}}>
                <h3>Google Calendar Events</h3>
                <ul>
                  {googleEventsByDate[selectedDate].map(ev => (
                    <li key={ev.id}>
                      <strong>{ev.title}</strong><br />
                      <div>
                        {formatEventForSelectedDay(ev.start, ev.end, selectedDate)}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <form className="check-in-form" onSubmit={handleSave}>
              <fieldset className="check-in-fieldset">
                <legend>Symptoms</legend>

                <label className="check-in-checkbox">
                  <input
                    type="checkbox"
                    name="daily_day_symp"
                    checked={formData.daily_day_symp}
                    onChange={updateField}
                  />

                  <span>Daytime asthma symptoms</span>
                </label>

                <label className="check-in-checkbox">
                  <input
                    type="checkbox"
                    name="daily_night_symp"
                    checked={formData.daily_night_symp}
                    onChange={updateField}
                  />

                  <span>Nighttime asthma symptoms</span>
                </label>

                <label className="check-in-checkbox">
                  <input
                    type="checkbox"
                    name="daily_limit_activity"
                    checked={formData.daily_limit_activity}
                    onChange={updateField}
                  />

                  <span>Symptoms limited my activity</span>
                </label>
              </fieldset>

              <label className="check-in-input-group">
                <span>Triggers</span>

                <input
                  type="text"
                  name="triggers"
                  value={formData.triggers}
                  onChange={updateField}
                  placeholder="Pollen, exercise, smoke"
                />

                <small>Separate multiple triggers with commas.</small>
              </label>

              <label className="check-in-input-group">
                <span>Calendar event</span>

                <input
                  type="text"
                  name="calendar_event"
                  value={formData.calendar_event}
                  onChange={updateField}
                  placeholder="Outdoor run, work shift, travel..."
                />
                <small className="check-in-field-hint">
                  Add what you have planned this day — we’ll use it in your advice.
                </small>
              </label>

              <label className="check-in-input-group">
                <span>Notes</span>

                <textarea
                  name="notes"
                  value={formData.notes}
                  onChange={updateField}
                  rows="4"
                  placeholder="Add anything you noticed about your symptoms."
                />
              </label>

              {error && <p className="calendar-error">{error}</p>}

              {saveMessage && (
                <p className="calendar-success">{saveMessage}</p>
              )}

              <div className="check-in-actions">
                <button
                  type="button"
                  className="check-in-cancel-button"
                  onClick={closeModal}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="check-in-save-button"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save check-in"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
      <SpinnerOverlay visible={eventsLoading} message="Loading Google Calendar events..." />
    </main>
  );
}

export default CalendarPage;