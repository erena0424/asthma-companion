import Checkbox from "./Checkbox";

function CheckboxList({
    options,
    selected,
    setSelected,
    theme = "light"
}) {

    function toggle(option) {

        if (selected.includes(option)) {
            setSelected(
                selected.filter(item => item !== option)
            );
        }
        else {
            setSelected([
                ...selected,
                option
            ]);
        }
    }


    return (
        <div className="vertical-16">
            {
                options.map(option => (
                    <Checkbox
                        key={option}
                        checked={selected.includes(option)}
                        onChange={() => toggle(option)}
                        theme={theme}
                    >
                        {option}
                    </Checkbox>
                ))
            }
        </div>
    );
}

export default CheckboxList;