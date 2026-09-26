import { useEffect } from "react";
import CheckboxList from "../../input/CheckboxList";

export function TrackingStep({
    formData,
    setFormData
}) {

    // Keep tracking in sync whenever symptoms change
    useEffect(() => {
        const tracking = formData.symptoms.filter(
            symptom => !formData.trackingExcluded.includes(symptom)
        );

        // Avoid unnecessary state updates
        if (
            tracking.length !== formData.tracking.length ||
            tracking.some(symptom => !formData.tracking.includes(symptom))
        ) {
            setFormData(prev => ({
                ...prev,
                tracking
            }));
        }
    }, [formData.symptoms, formData.trackingExcluded]);

    const setTrackedSymptoms = (tracking) => {
        setFormData(prev => ({
            ...prev,
            tracking,
            trackingExcluded: prev.symptoms.filter(
                symptom => !tracking.includes(symptom)
            )
        }));
    };

    return (
        <div className="vertical-fill vertical-24 at-top-center w-100">

            <p className="section-text">
                Which symptoms do you want to track?
            </p>

            <div className="at-top-center scrollable w-100">
                <CheckboxList
                    options={formData.symptoms}
                    selected={formData.tracking}
                    setSelected={setTrackedSymptoms}
                />
            </div>

            {
                formData.tracking.length == 0 ? 
                <p className="error-text-dark">You have no symptoms checked.</p>
                : <></>
            }

        </div>
    );
}

export default TrackingStep;