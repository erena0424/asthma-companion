import { Link } from "react-router";
import { urls } from "../../constants";
import "./PrivacyPage.css";

const LAST_UPDATED = "August 10, 2026";
const CONTACT_EMAIL = "support@lobelia.app";

function PrivacyPage() {
  return (
    <main className="privacy-page">
      <header className="privacy-header">
        <p className="privacy-brand">Lobelia</p>
        <h1>Privacy Policy</h1>
        <p className="privacy-updated">Last updated: {LAST_UPDATED}</p>
        <p className="privacy-intro">
          This Privacy Policy explains how Lobelia (“Lobelia,” “we,” “us,” or “our”) collects, uses, stores, and shares information when you use the Lobelia website and related services.
        </p>
        <p className="privacy-intro">
          Lobelia is a personal asthma self-management platform that combines information you provide with environmental conditions, planned activities, and other contextual information to provide personalized asthma risk forecasts and self-management support.
        </p>
        <p className="privacy-intro">
          Lobelia is not a medical device and does not diagnose, treat, cure, or prevent any disease. Lobelia does not replace professional medical advice or your asthma action plan.
        </p>
      </header>

      <section>
        <h2>1. Information We Collect</h2>
        <div className="d-flex vertical-16">
          <div>
            <h3><strong>Account Information</strong></h3>
            <p>When you create an account, we may collect:</p>
            <ul>
              <li>
                Email address
              </li>
              <li>
                Password, stored in hashed form
              </li>
              <li>
                Name and other optional profile information
              </li>
              <li>
                Profile photo URL, if you choose to add a profile photo
              </li>
              <li>
                Date of birth
              </li>
              <li>
                Emergency contact information
              </li>
              <li>
                Preferences, asthma triggers, and self-management goals
              </li>
            </ul>
          </div>
          <div>
            <h3><strong>Health and Symptom Information</strong></h3>
            <p>If you choose to use Lobelia's health-tracking features, you may provide information such as:</p>
            <ul>
              <li>
                Daily symptoms and symptom severity
              </li>
              <li>
                Activity limitations
              </li>
              <li>
                Asthma triggers
              </li>
              <li>
                Rescue inhaler use
              </li>
              <li>
                Personal notes
              </li>
              <li>
                Other information you choose to provide about your asthma or daily activities
              </li>
            </ul>
          </div>
          <div>
            <h3><strong>Optional Wearable and Activity Information</strong></h3>
            <p>If supported features are enabled, you may provide or sync summaries such as:</p>
            <ul>
              <li>
                Sleep duration
              </li>
              <li>
                Step count
              </li>
              <li>
                Activity information
              </li>
              <li>
                Heart-rate summaries
              </li>
            </ul>
          </div>
          <div>
            <h3><strong>Health and Symptom Information</strong></h3>
            <p>If you choose to use Lobelia's health-tracking features, you may provide information such as:</p>
            <ul>
              <li>
                Daily symptoms and symptom severity
              </li>
              <li>
                Activity limitations
              </li>
              <li>
                Asthma triggers
              </li>
              <li>
                Rescue inhaler use
              </li>
              <li>
                Personal notes
              </li>
              <li>
                Other information you choose to provide about your asthma or daily activities
              </li>
            </ul>
          </div>
          <div>
            <h3><strong>Location Information</strong></h3>
            <p>
              If you grant permission through your device or browser, Lobelia may receive approximate location information, such as latitude and longitude, to obtain relevant environmental information including weather, air quality, and pollen conditions.
            </p>
            <p>
              You may deny location access. Some features may use a fallback location or provide reduced functionality when location access is unavailable.
            </p>
          </div>
          <div>
            <h3><strong>Google Calendar Information</strong></h3>
            <p>
              If you choose to connect your Google Calendar, Lobelia requests read-only access to your calendar using Google's Calendar API.
            </p>
            <div style={{marginTop:25, marginBottom: 15}}>
              <p>
                With your permission, Lobelia may access calendar event information such as:
              </p>
              <ul>
                <li>
                  Event title
                </li>
                <li>
                  Date and time
                </li>
                <li>
                  Location
                </li>
                <li>
                  Description
                </li>
              </ul>
            </div>
            <p>
              Lobelia uses this information to provide more context-aware self-management guidance based on your planned activities.
            </p>
            <p>
              Lobelia does not request permission to modify, create, or delete your Google Calendar events.
            </p>
          </div>
          <div>
            <h3><strong>Chat and AI Feature Information</strong></h3>
            <div style={{marginBottom: 15}}>
              <p>
                If you use Lobelia's chat or AI-assisted features, we may process:
              </p>
              <ul>
                <li>
                  Messages you send
                </li>
                <li>
                  Information needed to respond to your request
                </li>
                <li>
                  Relevant context such as symptoms, forecasts, environmental conditions, planned activities, and information from your previous Lobelia records
                </li>
              </ul>
            </div>
            <p>
              Chat messages are used to generate responses and are not stored as a conversation history in Lobelia's database. Other information, such as check-ins, forecasts, and derived summaries, may be stored as described elsewhere in this Privacy Policy.
            </p>
          </div>
        </div>
      </section>

      <section>
        <h2>2. How We Use Information</h2>
        <p>We use information collected through Lobelia to:</p>
        <ul>
          <li>
            Create and manage your account
          </li>
          <li>
            Authenticate your account and provide account-related emails
          </li>
          <li>
            Process symptom and health information you choose to provide
          </li>
          <li>
            Generate short-term asthma risk forecasts
          </li>
          <li>
            Provide personalized self-management guidance
          </li>
          <li>
            Consider environmental conditions and planned activities when generating personalized guidance
          </li>
          <li>
            Retrieve relevant information from your previous records to provide more personalized responses
          </li>
          <li>
            Provide and maintain Google Calendar integration when you enable it
          </li>
          <li>
            Operate, maintain, and secure Lobelia
          </li>
          <li>
            Respond to requests and provide support
          </li>
          <li>
            Identify and address technical problems
          </li>
        </ul>
      </section>

      <section>
        <h2>3. AI and Third-Party Services</h2>
        <div style={{marginBottom: 15}}>
          <p>
            Lobelia uses third-party service providers to operate certain features of the platform. Depending on the features you use, these may include:
          </p>
          <ul>
            <li>
              <strong>Resend</strong> — used to send account verification and authentication emails.
            </li>
            <li>
              <strong>Google Gemini and/or Anthropic Claude</strong> — used to generate personalized guidance and responses and, where applicable, process information used for personalization and retrieval.
            </li>
            <li>
              <strong>Open-Meteo and/or OpenWeather</strong> — used to obtain weather and related environmental information.
            </li>
            <li>
              <strong>Google Pollen</strong> — used to obtain pollen information.
            </li>
            <li>
              <strong>Google Calendar API</strong> — used to provide the optional Google Calendar integration.
            </li>
            <li>
              <strong>Cloudinary</strong> — used to store profile images when the applicable feature is used.
            </li>
            <li>
              <strong>Hosting and cloud infrastructure providers</strong> — used to host the Lobelia website, backend services, and database.
            </li>
          </ul>
        </div>
        <p>
          Depending on the feature being used, information such as health-related context, environmental information, planned activities, or chat messages may be transmitted to third-party providers to perform the requested service.
        </p>
        <p>
          We do not sell your personal information.
        </p>
        <p>
          Third-party services may process information according to their own privacy policies and terms.
        </p>
      </section>

      <section>
        <h2>4. How We Store Information</h2>
        <div style={{marginBottom: 15}}>
          <p>
            Information stored by Lobelia may include:
          </p>
          <ul>
            <li>
              Account information
            </li>
            <li>
              Health and symptom logs
            </li>
            <li>
              Inhaler-use records
            </li>
            <li>
              Wearable and activity summaries
            </li>
            <li>
              Environmental information associated with forecasts
            </li>
            <li>
              Risk forecasts and personalized guidance
            </li>
            <li>
              Calendar connection information
            </li>
            <li>
              Relevant calendar information used in forecasts or guidance
            </li>
            <li>
              Derived summaries or embeddings used to retrieve relevant information from your previous records
            </li>
          </ul>
        </div>
        <p>
          We use hosted cloud infrastructure to store and process this information.
        </p>
        <p>
          Lobelia does not store your one-off chat messages as a persistent conversation history in its application database. However, information from your health logs, forecasts, calendar context, and other records may be stored separately and used to personalize future guidance.
        </p>
      </section>

      <section>
        <h2>5. Google Calendar</h2>
        <p>
          Google Calendar integration is optional.
        </p>
        <p>
          When you connect your Google Calendar, Lobelia requests the <strong style={{color:"var(--color-error-dark)"}}>calendar.readonly</strong> permission, which allows Lobelia to read calendar information but not modify your calendar.
        </p>
        <p>
          To maintain the connection, Lobelia stores the credentials necessary to access your Google Calendar, including an OAuth refresh token and associated Google account information.
        </p>
        <p>
          You can disconnect Google Calendar through the Lobelia application. When you disconnect it, Lobelia removes the stored Google Calendar connection credentials.
        </p>
        <p>
          Information that was previously incorporated into a forecast, check-in, or other stored record may remain in Lobelia after the Calendar connection is removed.
        </p>
      </section>

      <section>
        <h2>6. Data Retention</h2>
        <p>
          We retain account information and health, symptom, forecast, and related records while your account remains active or for as long as necessary to provide the services described in this Privacy Policy.
        </p>
        <p>
          Authentication and verification codes are short-lived and expire after approximately 10 minutes.
        </p>
        <p>
          Information associated with a disconnected Google Calendar may remain in previously stored forecasts, check-ins, or other records.
        </p>
        <p>
          Some information may be retained where necessary for security, legal, or operational purposes.
        </p>
      </section>

      <section>
        <h2>Your Choices</h2>
        <p>
          Depending on the features you use, you may:
        </p>
        <ul>
          <li>
            Choose whether to provide optional profile and health information
          </li>
          <li>
            Deny browser or device location access
          </li>
          <li>
            Choose whether to connect Google Calendar
          </li>
          <li>
            Disconnect Google Calendar through the application
          </li>
          <li>
            Update information in your profile and health logs
          </li>
        </ul>
      </section>

      <section>
        <h2>8. Security</h2>
        <p>
          We take reasonable measures to protect information handled by Lobelia.
        </p>
        <div style={{marginBottom: 15}}>
          <p>
            For example:
          </p>
          <ul>
            <li>
              Account passwords are stored in hashed form.
            </li>
            <li>
              Authentication uses login tokens.
            </li>
            <li>
              Data is stored using hosted cloud infrastructure with security controls provided by our infrastructure providers.
            </li>
            <li>
              Access to application services is restricted according to the needs of operating the platform.
            </li>
          </ul>
        </div>
        <p>
          However, no method of transmission or electronic storage is completely secure. We cannot guarantee the absolute security of information transmitted to or stored by Lobelia.
        </p>
      </section>

      <section>
        <h2>9. Medical Disclaimer</h2>
        <p>
          Lobelia provides personalized asthma self-management support and risk forecasts. Its content and recommendations are intended to support everyday self-management and are not a substitute for professional medical advice, diagnosis, treatment, or an asthma action plan.
        </p>
        <p>
          Lobelia is not a medical device and does not diagnose, treat, cure, or prevent any disease or medical condition.
        </p>
        <p>
          You should consult a qualified healthcare professional for medical decisions. If you experience a medical emergency, seek emergency medical care immediately.
        </p>
      </section>

      <section>
        <h2>10. Changes to This Privacy Policy</h2>
        <p>
          We may update this Privacy Policy from time to time to reflect changes to Lobelia, our practices, or applicable requirements.
        </p>
      </section>

      <footer className="privacy-footer">
        <Link to={urls.landing}>Back to Lobelia</Link>
      </footer>
    </main>
  );
}

export default PrivacyPage;
