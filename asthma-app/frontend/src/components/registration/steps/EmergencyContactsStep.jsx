import EmergencyContactsManager from "../../input/EmergencyContactsManager";

function EmergencyContactsStep({
  formData,
  setFormData,
}) {
  return (
    <div className="vertical-fill vertical-24 at-top-center">
      <p className="section-text">
        Who are your Emergency Contacts?
      </p>

      <EmergencyContactsManager
        contacts={formData.emergencyContacts ?? []}
        onChange={(contacts) =>
          setFormData({
            ...formData,
            emergencyContacts: contacts,
          })
        }
        compact={false}
      />
    </div>
  );
}

export default EmergencyContactsStep;