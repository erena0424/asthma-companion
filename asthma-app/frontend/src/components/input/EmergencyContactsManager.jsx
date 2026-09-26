import { useState } from "react";
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
}) {

  const [showModal, setShowModal] = useState(false);
  const [editingContact, setEditingContact] = useState(null);

  function openAddModal() {
    setEditingContact(null);
    setShowModal(true);
  }

  function openEditModal(contact) {
    setEditingContact(contact);
    setShowModal(true);
  }

  function closeModal() {
    setEditingContact(null);
    setShowModal(false);
  }

  function saveContact(contact) {
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

    onChange(updatedContacts);
    closeModal();
  }

  function removeContact(id) {
    onChange(
      contacts.filter(contact => contact.id !== id)
    );
  }

  return (
    <div className="vertical-16 at-middle-center vertical-fill">
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