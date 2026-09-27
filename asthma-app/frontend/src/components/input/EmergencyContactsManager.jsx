import { useState, useRef } from "react";
import { Button } from "react-bootstrap";
import ContactCard from "./ContactCard";
import ContactModal from "./ContactModal";

function EmergencyContactsManager({
  contacts = [],
  onChange,
  addButtonText = "Add Contact",
  emptyMessage = "No emergency contacts.",
  editable = true,
  compact = false,
  savedMessage = "",
}) {

  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingContact, setEditingContact] = useState(null);

  function openAddModal() {
    setEditingContact(null);
    setError("");
    setSaved(false);
    setShowModal(true);
  }

  function openEditModal(contact) {
    setEditingContact(contact);
    setError("");
    setSaved(false);
    setShowModal(true);
  }

  function closeModal() {
    setEditingContact(null);
    setShowModal(false);
  }

  async function persist(contacts) {
    if (busy.current) throw new Error("A contact save is already in progress.");
    busy.current = true;
    setPending(true);
    setError("");
    setSaved(false);
    try {
      await onChange(contacts);
      setSaved(true);
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  async function saveContact(contact) {
    let updatedContacts;

    if (editingContact) {
      updatedContacts = contacts.map(existing =>
        existing.id === contact.id
          ? contact
          : existing
      );
    } else {
      const id =
        crypto.randomUUID?.() ??
        String(Date.now());

      updatedContacts = [
        ...contacts,
        {
          ...contact,
          id,
        },
      ];
    }

    await persist(updatedContacts);
  }

  async function removeContact(id) {
    try {
      await persist(contacts.filter(contact => contact.id !== id));
    } catch (error) {
      setError(error.message || "Unable to remove contact. Your changes are not saved.");
    }
  }

  return (
    <div className="vertical-16 at-middle-center vertical-fill" aria-busy={pending}>
        {error && <p role="alert">{error}</p>}
        <p role="status">{pending ? "Saving contacts..." : saved ? savedMessage : ""}</p>
        <fieldset disabled={pending} style={{ border: 0, width: "100%" }}>
        <div
            className={`vertical-16 w-100 text-center ${
              contacts.length > 0 ? "scrollable" : ""
            }`}
        >
            {contacts.length === 0 ? (
                <p>{emptyMessage}</p>
             ) : (
                contacts.map(contact => (
                    <ContactCard
                        key={contact.id}
                        contact={contact}
                        onEdit={
                            editable
                            ? () => openEditModal(contact)
                            : undefined
                        }
                        onDelete={
                            editable
                            ? () => removeContact(contact.id)
                            : undefined
                        }
                        compact={compact}
                    />
                ))
            )}
        </div>

        {editable && (
            <Button
                className="button-dark btn-medium-text text-center"
                style={{
                    width: "clamp(200px, 40vw, 400px)",
                }}
                onClick={openAddModal}
            >
                {addButtonText}
            </Button>
        )}

        </fieldset>
        <ContactModal
            show={showModal}
            onHide={closeModal}
            onSubmit={saveContact}
            initialData={editingContact}
        />
    </div>
  );
}

export default EmergencyContactsManager;