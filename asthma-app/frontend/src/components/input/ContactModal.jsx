import { useState, useEffect, useRef } from "react";
import FormModal from "../input/FormModal";
import FormFull from "../input/FormFull";
import { contactFields, contactState } from "../../constants";
import { validate, hasErrors } from "../../helper-functions/validate";
import playErrorResponse from "../../helper-functions/playErrorResponse";


function ContactModal({
    show,
    onHide,
    onSubmit,
    initialData = null
}) {

    const submitting = useRef(false);
    const [pending, setPending] = useState(false);
    const isEditing = initialData !== null;

    const [formData, setFormData] = useState(contactState);
    const [errors, setErrors] = useState(contactState);

    const [buttonError, setButtonError] = useState("");
    const [shake, setShake] = useState(false);


    useEffect(() => {
        if (!show) return;

        const data = initialData ?? contactState;

        setFormData(data);

        const newErrors = validate(
            contactFields,
            data
        );

        setErrors(newErrors);
        setButtonError("");

    }, [show, initialData]);


    async function submit() {
        if (submitting.current) return;
        const newErrors = validate(
            contactFields,
            formData
        );

        setErrors(newErrors);

        if (hasErrors(newErrors)) {
            setButtonError(
                "You have not met the requirements."
            );

            playErrorResponse(setShake);
            return;
        }


        submitting.current = true;
        setPending(true);
        setButtonError("");
        try {
            await onSubmit(formData);
            onHide();
        } catch (error) {
            setButtonError(error.message || "Unable to save contact. Your changes are not saved.");
        } finally {
            submitting.current = false;
            setPending(false);
        }

    }


    if (!show) return null;


    return (
        <FormModal
            title={isEditing ? "Edit Contact" : "Add Contact"}
            onHide={() => { if (!submitting.current) onHide(); }}
            onSubmit={submit}
            pending={pending}
            submitText={pending ? "Saving..." : isEditing ? "Save Changes" : "Add"}
            buttonError={buttonError}
            shake={shake}
        >
            <fieldset disabled={pending} style={{ border: 0 }}>
            <FormFull
                theme="light"
                fields={contactFields}
                formData={formData}
                setFormData={setFormData}
                errors={errors}
                setErrors={setErrors}
                setInputError={setButtonError}
            />
            </fieldset>
        </FormModal>
    );
}

export default ContactModal;