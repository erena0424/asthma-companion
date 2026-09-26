import { Form } from 'react-bootstrap';
import { useEffect, useState } from 'react';
import { errorIconDataUri } from '../../helper-functions/errorIconDataUri.js';
import { getColor } from '../../helper-functions/getColor';
import { validate } from '../../helper-functions/validate.js';
import { IMaskInput } from "react-imask";
import { Eye, EyeSlash } from "react-bootstrap-icons";

function FormFull( { fields, formData, setFormData, errors, setErrors, setInputError, theme = "dark" } ) {
    
    // test whether input meets requirements
    const handleChange = (name, value) => {
        const newData = {
            ...formData,
            [name]: value,
        };

        setFormData(newData);

        const newErrors = validate(fields, newData);

        setErrors(newErrors);
        setInputError("");
    };

    // visibility
    const [showPasswords, setShowPasswords] = useState({});
    const togglePassword = (name) => {
        setShowPasswords((prev) => ({
            ...prev,
            [name]: !prev[name],
        }));
    };

    // get color and shape for error icon
    var contrast = (theme == "light") ? "dark" : "light";
    const color = getColor(`--color-error-${contrast}`);
    const icon = errorIconDataUri(color);

    // apply error icon
    useEffect(() => {
        document.querySelectorAll('.form-control').forEach(el => {
            if (el.classList.contains('is-invalid')) {
                // apply icon
                el.style.backgroundImage = icon;
                el.style.backgroundRepeat = "no-repeat";
                el.style.backgroundPosition = "right .75rem center";
                el.style.backgroundSize = "1rem";
            } else {
                // remove icon
                el.style.backgroundImage = "";
                el.style.backgroundRepeat = "";
                el.style.backgroundPosition = "";
                el.style.backgroundSize = "";
            }
        });
    }, [errors]);

    return (
        <div
            className={`form-full ${theme} vertical-24 flex-fill`}
            style={{ justifyContent: "space-evenly" }}
        >
        {
            fields.map((data) => (
                <Form.Group key={data.name} className="form-item">
                    <Form.Label>{data.label}</Form.Label>

                    {
                        data.type === "tel" ? (
                        <Form.Control
                            as={IMaskInput}
                            mask="(000) 000-0000"
                            lazy={true}
                            placeholder="(XXX) XXX-XXXX"
                            value={formData[data.name] ?? ""}
                            onAccept={(value) => handleChange(data.name, value)}
                            isInvalid={!!errors[data.name]}
                            className={`${theme}`}
                        />
                        ) : (
                        <div className={`${data.type === "password" ? "password-wrapper" : ""}`}>
                            <Form.Control
                                type={
                                    data.type === "password" && showPasswords[data.name]
                                        ? "text"
                                        : data.type
                                }
                                placeholder={data.placeholder}
                                value={formData[data.name] ?? ""}
                                onChange={(e) => handleChange(data.name, e.target.value)}
                                onBlur={(e) => handleChange(data.name, e.target.value.trim())}
                                isInvalid={!!errors[data.name]}
                                className={`${theme}`}
                            />

                            {data.type === "password" && (
                                <button
                                    type="button"
                                    className="password-toggle"
                                    onClick={() => togglePassword(data.name)}
                                    aria-label={
                                        showPasswords[data.name]
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                >
                                    {showPasswords[data.name] ? (
                                        <EyeSlash />
                                    ) : (
                                        <Eye />
                                    )}
                                </button>
                            )}
                        </div>
                        )
                    }

                    <Form.Control.Feedback type="invalid">
                        {errors[data.name]}
                    </Form.Control.Feedback>
                </Form.Group>
            ))}
        </div>  
    );
}

export default FormFull;