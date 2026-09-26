import CheckboxList from "../../input/CheckboxList";
import { asthmaTriggers } from "../../../constants";

export function TriggersStep({
    formData,
    setFormData
}) {

    const setTriggers = (triggers) => {
        setFormData(prev => ({
            ...prev,
            triggers
        }));
    };

    return(
        <div className="vertical-fill vertical-24 at-top-center w-100">

            <p className="section-text">
                Which asthma triggers do you have?
            </p>

            <div className="at-top-center scrollable w-100">
                <CheckboxList
                    options={asthmaTriggers}
                    selected={formData.triggers}
                    setSelected={setTriggers}
                />
            </div>

        </div>
    );
}

export default TriggersStep;