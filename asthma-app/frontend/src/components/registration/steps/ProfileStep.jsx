import { profileFields, profileState } from '../../../constants';
import { useEffect } from 'react';
import FormFull from "../../input/FormFull";
import { validate } from '../../../helper-functions/validate';

export function ProfileStep({
    formData,
    setFormData,
    errors,
    setErrors,
    setButtonError
}) {

    // validate errors immediately
    useEffect(() => {
        const newErrors = validate(profileFields, formData);

        setErrors(newErrors);
        setButtonError("");
}, []);

    return(
        <div className="text-start flex-grow-1">
            <FormFull
              theme={"dark"}
              fields={profileFields}
              formData={formData}
              setFormData={setFormData}
              errors={errors}
              setErrors={setErrors}
              setInputError={setButtonError}
            />
        </ div>
    );
}

export default ProfileStep;