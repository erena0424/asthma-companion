import CheckboxList from "../../input/CheckboxList";
import { asthmaSymptoms } from "../../../constants";

export function SymptomsStep({
    formData,
    setFormData
}) {

    const setSymptoms = (symptoms) => {
        setFormData(prev => ({
            ...prev,
            symptoms
        }));
    };

    return(
        <div className="vertical-fill vertical-24 at-top-center w-100">

            <p className="section-text">
                Which asthma symptoms do you experience?
            </p>

            <div className="at-top-center scrollable w-100">
                <CheckboxList
                    options={asthmaSymptoms}
                    selected={formData.symptoms}
                    setSelected={setSymptoms}
                />
            </div>

        </div>
    );
}

export default SymptomsStep;