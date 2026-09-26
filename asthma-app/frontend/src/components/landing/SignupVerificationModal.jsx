import { useEffect, useState } from "react";
import FormModal from "../input/FormModal";
import FormFull from "../input/FormFull";
import playErrorResponse from "../../helper-functions/playErrorResponse";
import { requestSignupCode, verifySignupCode } from "../../helper-functions/authentication";
import { validate, hasErrors } from "../../helper-functions/validate";

const codeFields = [
  {
    name: "code",
    label: "Verification Code",
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

function SignupVerificationModal({ show, email, onHide, onConfirm }) {
  const [formData, setFormData] = useState({ code: "" });
  const [errors, setErrors] = useState({ code: "" });
  const [buttonError, setButtonError] = useState("");
  const [shake, setShake] = useState(false);

  if (!show) return null;

  function submit() {
    const newErrors = validate(codeFields, formData);
    setErrors(newErrors);

    if (hasErrors(newErrors)) {
      setButtonError("You have not met the requirements.");
      playErrorResponse(setShake);
      return;
    }

    (async () => {
      const result = await verifySignupCode(email, formData.code);

      if (result !== true) {
        setButtonError(result);
        playErrorResponse(setShake);
        return;
      }

      onHide();
      onConfirm();
    })();
  }

  return (
    <FormModal
      title="Verify Sign Up"
      onHide={onHide}
      onSubmit={submit}
      submitText="Continue"
      buttonError={buttonError}
      shake={shake}
    >
      <div className="vertical-16 flex-fill">
        <p className="m-0 text-center" style={{ color: "var(--color-primary)", fontSize: "18px" }}>
          A confirmation code was sent to {email}. Enter it below to finish creating your account.
        </p>

        <FormFull
          theme="light"
          fields={codeFields}
          formData={formData}
          setFormData={setFormData}
          errors={errors}
          setErrors={setErrors}
          setInputError={setButtonError}
        />
      </div>
    </FormModal>
  );
}

export default SignupVerificationModal;