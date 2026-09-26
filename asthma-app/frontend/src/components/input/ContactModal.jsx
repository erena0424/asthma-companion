import { useState, useEffect } from "react";
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


    function submit() {
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


        onSubmit(formData);

        setFormData(contactState);
        setErrors(contactState);
        setButtonError("");

        onHide();
    }


    if (!show) return null;


    return (
        <FormModal
            title={isEditing ? "Edit Contact" : "Add Contact"}
            onHide={onHide}
            onSubmit={submit}
            submitText={isEditing ? "Edit" : "Add"}
            buttonError={buttonError}
            shake={shake}
        >
            <FormFull
                theme="light"
                fields={contactFields}
                formData={formData}
                setFormData={setFormData}
                errors={errors}
                setErrors={setErrors}
                setInputError={setButtonError}
            />
        </FormModal>
    );
}

export default ContactModal;