import { useEffect, useState } from "react";
import FormModal from "../input/FormModal";
import FormFull from "../input/FormFull";
import playErrorResponse from "../../helper-functions/playErrorResponse";
import { loginFields, signUpFields } from "../../constants";
import { validate, hasErrors } from "../../helper-functions/validate";
import { requestResetCode, verifyResetCode, resetPassword } from "../../helper-functions/authentication";

const emailFields = [loginFields[0]];
const codeFields = [
  {
    name: "code",
    label: "Reset Code",
    type: "text",
    placeholder: "Enter the code from your email",
    error: (value) => {
      if (!value) {
        return "Code is required.";
      }

      return "";
    }
  }
];
const passwordFields = signUpFields.slice(1);

function ForgotPasswordModal({ show, onHide }) {
  const [step, setStep] = useState("email");
  const [emailData, setEmailData] = useState({ email: "" });
  const [emailErrors, setEmailErrors] = useState({ email: "" });
  const [codeData, setCodeData] = useState({ code: "" });
  const [codeErrors, setCodeErrors] = useState({ code: "" });
  const [passwordData, setPasswordData] = useState({ password: "", confirmPassword: "" });
  const [passwordErrors, setPasswordErrors] = useState({ password: "", confirmPassword: "" });
  const [buttonError, setButtonError] = useState("");
  const [shake, setShake] = useState(false);
  const [loadingCode, setLoadingCode] = useState(false);

  useEffect(() => {
    if (!show) {
      return;
    }

    setStep("email");
    setEmailData({ email: "" });
    setEmailErrors({ email: "" });
    setCodeData({ code: "" });
    setCodeErrors({ code: "" });
    setPasswordData({ password: "", confirmPassword: "" });
    setPasswordErrors({ password: "", confirmPassword: "" });
    setButtonError("");
    setShake(false);
  }, [show]);

  if (!show) {
    return null;
  }

  async function submit() {
    if (loadingCode) return;

    setLoadingCode(true);

    try {
      if (step === "email") {
        const newErrors = validate(emailFields, emailData);

        setEmailErrors(newErrors);

        if (hasErrors(newErrors)) {
          setButtonError("You have not met the requirements.");
          playErrorResponse(setShake);
          return;
        }

        const result = await requestResetCode(emailData.email);

        if (result !== true) {
          setButtonError(result);
          playErrorResponse(setShake);
          return;
        }

        setButtonError("");
        setStep("code");
        return;
      }

      if (step === "code") {
        const newErrors = validate(codeFields, codeData);

        setCodeErrors(newErrors);

        if (hasErrors(newErrors)) {
          setButtonError("You have not met the requirements.");
          playErrorResponse(setShake);
          return;
        }

        const result = await verifyResetCode(emailData.email, codeData.code);

        if (result !== true) {
          setButtonError(result);
          playErrorResponse(setShake);
          return;
        }

        setButtonError("");
        setStep("password");
        return;
      }

      const newErrors = validate(passwordFields, passwordData);

      setPasswordErrors(newErrors);

      if (hasErrors(newErrors)) {
        setButtonError("You have not met the requirements.");
        playErrorResponse(setShake);
        return;
      }

      const result = await resetPassword(
        emailData.email,
        passwordData.password,
        codeData.code
      );

      if (result === true) {
        onHide();
        return;
      }

      setButtonError(result);
      playErrorResponse(setShake);

    } finally {
      setLoadingCode(false);
    }
  }

  const title = step === "email" ? "Forgot Password" : step === "code" ? "Verify Reset Code" : "Reset Password";
  const submitText = step === "email" ? "Send Code" : step === "code" ? "Verify Code" : "Reset Password";

  return (
    <FormModal
      title={title}
      onHide={onHide}
      onSubmit={submit}
      submitText={loadingCode ? "Sending..." : submitText}
      buttonError={buttonError}
      shake={shake}
    >
      <div className="vertical-16 flex-fill">
        {step === "email" && (
          <p className="m-0 text-center" style={{ color: "var(--color-primary)", fontSize: "18px" }}>
            Enter the email tied to your account. A reset code will be sent there if the email exists.
          </p>
        )}
        {step === "code" && (
          <p className="m-0 text-center" style={{ color: "var(--color-primary)", fontSize: "18px" }}>
            Enter the reset code that was sent to {emailData.email}.
          </p>
        )}
        {step === "password" && (
          <p className="m-0 text-center" style={{ color: "var(--color-primary)", fontSize: "18px" }}>
            Choose a new password for {emailData.email}.
          </p>
        )}

        {step === "email" && (
          <FormFull
            theme="light"
            fields={emailFields}
            formData={emailData}
            setFormData={setEmailData}
            errors={emailErrors}
            setErrors={setEmailErrors}
            setInputError={setButtonError}
          />
        )}

        {step === "code" && (
          <FormFull
            theme="light"
            fields={codeFields}
            formData={codeData}
            setFormData={setCodeData}
            errors={codeErrors}
            setErrors={setCodeErrors}
            setInputError={setButtonError}
          />
        )}

        {step === "password" && (
          <FormFull
            theme="light"
            fields={passwordFields}
            formData={passwordData}
            setFormData={setPasswordData}
            errors={passwordErrors}
            setErrors={setPasswordErrors}
            setInputError={setButtonError}
          />
        )}
      </div>
    </FormModal>
  );
}

export default ForgotPasswordModal;