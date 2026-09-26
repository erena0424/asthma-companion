import { useState, useEffect } from "react";
import Registration from "../registration/Registration";
import WelcomeStep from "../registration/steps/WelcomeStep";
import ProfileStep from "../registration/steps/ProfileStep";
import EmergencyContactsStep from "../registration/steps/EmergencyContactsStep";
import TriggersStep from "../registration/steps/TriggersStep";
import SymptomsStep from "../registration/steps/SymptomsStep";
import TrackingStep from "../registration/steps/TrackingStep";
import FinishStep from "../registration/steps/FinishStep";
import { profileState, urls } from "../../constants";
import playErrorResponse from "../../helper-functions/playErrorResponse";
import { useNavigate } from "react-router";
import { updateProfile } from "../../helper-functions/updateProfile";
import { useAuth } from "../../context/AuthContext";

function SetupPage() {
    // get user token
    const { token, setupComplete, setSetupComplete, updateUser } = useAuth();

    // number of pages to go through
    const numPages = 7;
    const [numPage, setNumPage] = useState(0);

    const [setupData, setSetupData] = useState({
        ...profileState,
        emergencyContacts: [],
        triggers: [],
        symptoms: [],
        tracking: [],
        trackingExcluded: []
    });

    // final setup
    const navigate = useNavigate();
    const [saving, setSaving] = useState(false);

    // navigate to home page when setupComplete changes to true
    useEffect(() => {
        if (setupComplete) {
            navigate(urls.home);
        }
    }, [setupComplete]);

    // error handling
    const [errors, setErrors] = useState({});
    const [buttonError, setButtonError] = useState("");
    const [shake, setShake] = useState(false);

    const nextPage = async () => {
        if (!canContinue) {
            setButtonError("Please complete all required fields.");
            playErrorResponse(setShake);
            return;
        }

        // Leaving TrackingStep
        if (numPage === numPages - 2) {
            try {
                setSaving(true);

                const updatedUser = await updateProfile({
                    name: setupData.name,
                    date_of_birth: setupData.date_of_birth,

                    emergency_contacts: setupData.emergencyContacts,

                    trigger_preferences: setupData.triggers,

                    symptoms: setupData.symptoms,

                    tracking: setupData.tracking,
                }, token);

                // update context
                updateUser(updatedUser);

                setNumPage(numPage + 1);
                setButtonError("");
                setErrors({});
            }
            catch (err) {
                setButtonError(
                    "Unable to save your information. Please try again."
                );

                console.log(err);

                playErrorResponse(setShake);
            }
            finally {
                setSaving(false);
            }

            return;
        }

        // Leaving FinishStep
        if (numPage === numPages - 1) {
            setSetupComplete(true);
            return;
        }

        // All other pages
        setNumPage(numPage + 1);

        // reset errors
        setErrors({});
        setButtonError("");
    };

    const prevPage = () => {
        if (numPage > 0) {
            setNumPage(numPage - 1);
            
            // reset errors
            setErrors({});
            setButtonError("");
        }
    };

    const pages = [
        <WelcomeStep />,
        <ProfileStep
            formData={setupData}
            setFormData={setSetupData}
            errors={errors}
            setErrors={setErrors}
            setButtonError={setButtonError}
        />,
        <EmergencyContactsStep
            formData={setupData}
            setFormData={setSetupData}
            errors={errors}
            setErrors={setErrors}
            setButtonError={setButtonError}
        />,
        <TriggersStep
            formData={setupData}
            setFormData={setSetupData}
            errors={errors}
            setErrors={setErrors}
            setButtonError={setButtonError}
        />,
        <SymptomsStep
            formData={setupData}
            setFormData={setSetupData}
            errors={errors}
            setErrors={setErrors}
            setButtonError={setButtonError}
        />,
        <TrackingStep
            formData={setupData}
            setFormData={setSetupData}
            errors={errors}
            setErrors={setErrors}
            setButtonError={setButtonError}
        />,
        <FinishStep data={setupData}
            formData={setupData}
            setFormData={setSetupData}
            errors={errors}
            setErrors={setErrors}
            setButtonError={setButtonError}
        />,
    ];

    const canContinue = Object.values(errors).every(error => !error);

    return (
        <Registration
            numPage={numPage}
            numPages={numPages}
            onNext={nextPage}
            onBack={prevPage}
            nextDisabled={!canContinue}
            buttonError={buttonError}
            shake={shake}
            saving={saving}
        >
            {pages[numPage]}
        </Registration>
    );
}

export default SetupPage;