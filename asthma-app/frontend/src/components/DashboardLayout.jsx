import { useState, useEffect, useRef } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router';
import { Container, Nav, Navbar } from 'react-bootstrap';
import { urls } from "../constants";
import { useAuth } from "../context/AuthContext";
import ProfileCircle from "./input/ProfileCircle";
import FormModal from "./input/FormModal";
import Chatbot from './input/Chatbot';
import useIsSmallScreen from "../helper-functions/useIsSmallScreen";

function DashboardLayout() {
  const location = useLocation();
  const { token, user, logout, refreshUserProfile } = useAuth();
  const isSmallScreen = useIsSmallScreen();

  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [navbarExpanded, setNavbarExpanded] = useState(false);

  const navbarRef = useRef(null);

  useEffect(() => {
    refreshUserProfile();
  }, [token, refreshUserProfile]);

  // Collapse navbar when clicking outside of it
  useEffect(() => {
    if (!isSmallScreen || !navbarExpanded) {
      return;
    }

    function handleClickOutside(event) {
      if (
        navbarRef.current &&
        !navbarRef.current.contains(event.target)
      ) {
        setNavbarExpanded(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, [isSmallScreen, navbarExpanded]);

  // Collapse navbar whenever the route changes
  useEffect(() => {
    setNavbarExpanded(false);
  }, [location.pathname]);

  const pageNames = {
    [urls.home]: `Hi, ${user?.name || "User"}!`,
    [urls.statistics]: "Your Statistics",
    [urls.calendar]: "Calendar",
    [urls.profile]: "Profile",
    [urls.chat]: "Chat",
  };

  const currentPage = pageNames[location.pathname];

  function openLogoutModal() {
    setShowLogoutModal(true);
  }

  function closeLogoutModal() {
    setShowLogoutModal(false);
  }

  function confirmLogout() {
    logout();
    setShowLogoutModal(false);
  }

  return (
    <>
      {/* Navbar */}
      <div
        ref={navbarRef}
        className="dashboard-navbar"
        style={{
          backgroundColor: "var(--color-tertiary-dark)",
        }}
      >
        <Navbar
          expand="md"
          expanded={navbarExpanded}
          onToggle={setNavbarExpanded}
        >
          <Navbar.Toggle aria-controls="dashboard-navbar-nav" />

          <Navbar.Collapse id="dashboard-navbar-nav">
            <Nav className="w-100">
              <Nav.Link as={NavLink} to={urls.home} end>
                Home
              </Nav.Link>

              <Nav.Link as={NavLink} to={urls.statistics} end>
                Statistics
              </Nav.Link>

              <Nav.Link as={NavLink} to={urls.calendar} end>
                Calendar
              </Nav.Link>

              <Nav.Link as={NavLink} to={urls.profile} end>
                Profile
              </Nav.Link>

              {isSmallScreen && (
                <Nav.Link as={NavLink} to={urls.chat} end>
                  Chat
                </Nav.Link>
              )}
            </Nav>
          </Navbar.Collapse>
        </Navbar>
      </div>

      {/* Floating chatbot on larger screens */}
      {!isSmallScreen && (
        <Chatbot
          title="Chat"
          isFloating={true}
          beginClosed={false}
        />
      )}

      {/* Header */}
      <div className="p-4">
        <div
          className="horizontal at-middle-center"
          style={{ justifyContent: "space-between" }}
        >
          <h1>{currentPage}</h1>

          <ProfileCircle
            imageUrl={`${import.meta.env.BASE_URL}lobelia_icon_fill.png`}
            onClick={openLogoutModal}
            theme="green-theme"
          />
        </div>

        <hr />
      </div>

      {/* Content */}
      <Container fluid className="w-100 p-0">
        <Outlet />
      </Container>

      {/* Logout Confirmation */}
      {showLogoutModal && (
        <FormModal
          title="Logout?"
          onHide={closeLogoutModal}
          onSubmit={confirmLogout}
          submitText="Logout"
        >
          <div className="at-middle-center vertical-16">
            <p className="text-center">
              Are you sure you want to log out?
            </p>
          </div>
        </FormModal>
      )}
    </>
  );
}

export default DashboardLayout;