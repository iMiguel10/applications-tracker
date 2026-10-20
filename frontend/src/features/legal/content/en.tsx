import { Link } from "react-router-dom";

import { providerName } from "@/features/ai/lib/providers";
import { legalPath } from "../lib/legalPages";
import type { LegalContent, LegalContext } from "./types";

/* Legal texts in English (issue #3, decision 0026). A base that whoever deploys must
 * review: not legal advice. Whatever depends on the installation comes from the
 * context; nothing is made up. */

function operator({ legal }: LegalContext) {
  return (
    <ul>
      <li>
        <strong>Owner:</strong> {legal.operator_name}
        {legal.tax_id && <> (tax ID {legal.tax_id})</>}
      </li>
      {legal.address && (
        <li>
          <strong>Address:</strong> {legal.address}
        </li>
      )}
      <li>
        <strong>Contact:</strong>{" "}
        <a href={`mailto:${legal.contact_email}`}>{legal.contact_email}</a>
      </li>
    </ul>
  );
}

const authority = ({ legal }: LegalContext) =>
  legal.supervisory_authority ?? "the Spanish Data Protection Agency (AEPD, www.aepd.es)";

function aiRecipients({ legal }: LegalContext) {
  const platform = legal.ai_platform_provider;
  const ownKeys = legal.ai_own_key_providers;
  if (!platform && ownKeys.length === 0) return null;
  return (
    <>
      {platform && platform !== "ollama" && (
        <li>
          <strong>{providerName(platform)}</strong>, this installation's artificial intelligence
          provider, when you ask for a proposal with the free uses. It receives your professional
          profile <strong>without your contact details</strong> and the job description. It is in
          the United States: the transfer relies on the EU-US Data Privacy Framework or on
          standard contractual clauses.
        </li>
      )}
      {platform === "ollama" && (
        <li>
          The artificial intelligence server (Ollama) run by the owner, when you ask for a
          proposal with the free uses. It receives your professional profile{" "}
          <strong>without your contact details</strong> and the job description.
        </li>
      )}
      {ownKeys.length > 0 && (
        <li>
          If you use <strong>your own key</strong> for{" "}
          {new Intl.ListFormat("en", { type: "disjunction" }).format(ownKeys.map(providerName))},
          the same data goes to your account with that provider, under your own contract with it.
          Your key is stored encrypted and never shown.
        </li>
      )}
    </>
  );
}

const content: LegalContent = {
  notice: (context) => (
    <>
      <h2>Owner</h2>
      <p>This installation of Applications Tracker ({context.site}) is offered and run by:</p>
      {operator(context)}
      <p>
        Applications Tracker is a program its author publishes for anyone to install. The author
        does not run this installation and has no access to its data: the owner is responsible
        for it.
      </p>

      <h2>Purpose</h2>
      <p>
        The application is for recording and following your job applications: the applications,
        their statuses, interviews, reminders, your CVs and your cover letters. Its use is
        governed by the <Link to={legalPath("terms")}>terms and conditions</Link> and the{" "}
        <Link to={legalPath("privacy")}>privacy policy</Link>.
      </p>

      <h2>Links to other sites</h2>
      <p>
        The application stores the links to the job offers you add. The owner is not responsible
        for the content of those sites.
      </p>

      <h2>Governing law</h2>
      <p>This notice is governed by Spanish law.</p>
    </>
  ),

  privacy: (context) => {
    const { legal, emailEnabled } = context;
    return (
      <>
        <h2>Who processes your data</h2>
        <p>The data controller is the owner of this installation:</p>
        {operator(context)}

        <h2>What data we process</h2>
        <ul>
          <li>
            <strong>Your account:</strong> your email and your password, stored hashed so that
            nobody can read it.
          </li>
          <li>
            <strong>What you record:</strong> companies, applications and their history,
            interviews, reminders and notes.
          </li>
          <li>
            <strong>Your professional profile and your documents:</strong> the contact details you
            add, your experience, education, skills and languages, and the PDFs you upload or
            generate.
          </li>
          <li>
            <strong>Your preferences:</strong> language, time zone and notifications.
          </li>
          {(legal.ai_platform_provider || legal.ai_own_key_providers.length > 0) && (
            <li>
              <strong>Your use of artificial intelligence:</strong> the proposals you ask for, what
              they generate and your consents.
            </li>
          )}
          <li>
            <strong>Technical data:</strong> your IP, the requested address and your browser in
            the server logs, and your IP and email in sign-in attempts, to stop abuse.
          </li>
        </ul>

        <h2>What for, and on what basis</h2>
        <ul>
          <li>
            <strong>Providing the service</strong> (your account and everything you store): it is
            necessary for the contract you accept by using it.
          </li>
          {emailEnabled && (
            <li>
              <strong>Sending you email notifications</strong> (reminders, interviews, digests):
              they are part of the service and each one can be turned off in Preferences.
            </li>
          )}
          {(legal.ai_platform_provider || legal.ai_own_key_providers.length > 0) && (
            <li>
              <strong>Tailoring your CV or writing cover letters with artificial intelligence:</strong>{" "}
              only with your consent, which is asked for each provider before sending it anything
              and which you can withdraw at any time.
            </li>
          )}
          <li>
            <strong>Protecting the application</strong> (request limits and logs): legitimate
            interest in keeping it secure.
          </li>
          <li>
            <strong>Backups,</strong> to recover your data if something fails: legitimate interest
            and security duty.
          </li>
        </ul>

        <h2>Who receives it</h2>
        <p>
          Your data is not sold or shared. It is only received, for the stated purposes, by the
          providers that help the owner provide the service:
        </p>
        <ul>
          <li>The server hosting, if the owner doesn't run it themselves.</li>
          {emailEnabled && (
            <li>The email service, which receives your email and the content of your notifications.</li>
          )}
          {aiRecipients(context)}
        </ul>

        <h2>For how long</h2>
        <ul>
          <li>
            What you store, until you delete it or delete your account. When you delete it, it
            disappears from the application at once and stays at most{" "}
            <strong>{legal.backup_retention_days} days</strong> in the backups, until they expire.
          </li>
          {emailEnabled && <li>The record of notifications sent, 90 days.</li>}
          <li>Technical data, only as long as needed for security.</li>
        </ul>

        <h2>Your rights</h2>
        <p>
          You can access your data, rectify it, erase it, object to its processing, ask for it to
          be restricted, take it with you (portability) and withdraw your consent:
        </p>
        <ul>
          <li>
            <strong>Download all of it</strong> in Preferences, with “Download all my data”.
          </li>
          <li>
            <strong>Correct it</strong> in the application itself. To change your email, write to
            the owner.
          </li>
          <li>
            <strong>Delete it</strong> with “Delete account”, in Preferences.
          </li>
          <li>
            For any other request, write to{" "}
            <a href={`mailto:${legal.contact_email}`}>{legal.contact_email}</a>. We will answer
            within one month at most.
          </li>
        </ul>
        <p>If you think your rights are not respected, you can complain to {authority(context)}.</p>

        <h2>Minors</h2>
        <p>The application is not for anyone under 14.</p>

        <h2>Security</h2>
        <p>
          The connection is encrypted (HTTPS), passwords are stored hashed, artificial
          intelligence keys encrypted, and backups are made every day.
        </p>

        <h2>Changes</h2>
        <p>If this policy changes in anything important, we will ask you to accept it again when you sign in.</p>
      </>
    );
  },

  terms: (context) => (
    <>
      <h2>The service</h2>
      <p>
        The owner of this installation ({context.legal.operator_name}) offers you Applications
        Tracker to organise your job search. It is offered <strong>as is</strong>: every effort is
        made for it to work and for your data to be safe, but it is not guaranteed to be always
        available or free of errors. Download your data now and then if it matters to you.
      </p>

      <h2>Your account</h2>
      <ul>
        <li>It is personal: don't share it. You must be at least 14 years old.</li>
        <li>Look after your password. What is done with your account is your responsibility.</li>
      </ul>

      <h2>Acceptable use</h2>
      <p>You may not use the application to:</p>
      <ul>
        <li>Store or share illegal content, or other people's data without the right to do so.</li>
        <li>Upload harmful files or try to access what isn't yours.</li>
        <li>Overload it or get around its limits.</li>
      </ul>

      <h2>Your content</h2>
      <p>
        What you store is yours. It is only used to provide the service: storing it, showing it to
        you, generating your PDFs and, if you ask, sending it to the artificial intelligence.
      </p>

      <h2>Artificial intelligence</h2>
      <p>
        CV and cover letter proposals are generated by an artificial intelligence and may contain
        mistakes. Review them before using them: you decide what you send to each company and you
        are responsible for it being true.
      </p>

      <h2>Leaving and suspension</h2>
      <p>
        You can delete your account whenever you want, from Preferences. The owner may suspend or
        delete an account that breaches these terms, letting you know where possible.
      </p>

      <h2>Liability</h2>
      <p>
        The owner is not liable for damage arising from misuse of the application or from it being
        unavailable, except where the law does not allow this to be limited.
      </p>

      <h2>Changes</h2>
      <p>If these terms change in anything important, we will ask you to accept them again when you sign in.</p>

      <h2>Governing law</h2>
      <p>
        They are governed by Spanish law. If you are a consumer, you can go to the courts where you
        live.
      </p>
    </>
  ),

  cookies: () => (
    <>
      <h2>What we store in your browser</h2>
      <ul>
        <li>
          <strong>Session cookies:</strong> they keep you signed in. They are strictly necessary:
          without them you couldn't sign in.
        </li>
        <li>
          <strong>Interface preferences</strong> (in the browser's storage, not cookies): the light
          or dark theme, the language of the access screens, the folded board columns and the AI
          proposals in progress.
        </li>
      </ul>

      <h2>What there isn't</h2>
      <p>
        No analytics, no advertising, no third-party cookies. That's why we don't ask you to accept
        cookies: the ones there are, the application can't work without.
      </p>

      <h2>How to delete them</h2>
      <p>
        From your browser settings. If you delete the session cookies, you will have to sign in
        again.
      </p>
    </>
  ),
};

export default content;
