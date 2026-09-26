export function validate(fields, data) {
    const errors = {};

    fields.forEach(field => {
        errors[field.name] = field.error(
            data[field.name],
            data
        );
    });

    return errors;
}

export function hasErrors(errors) {
    return Object.values(errors).some(error => error);
}