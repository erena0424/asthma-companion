import { Container } from 'react-bootstrap';
import ArrowButton from '../input/ArrowButton';
import AuthForm from './AuthForm';
import About from './About';

function LandingSlide({ showLogin, showSignUp, onBack, landingVisible }) {

  return (
    <>
      <Container
        fluid
        className="dark-green-body p-5 vertical min-vh-100 h-100 position-relative"
        style={{
          overflowY: "auto",
        }}
      >
        {
          // back button will be placed in top-left corner absolutely (without affecting placement of other items)
          !landingVisible && <ArrowButton className="button-light p-2 absolute-top-left" isBack={true} onClick={onBack} />
        }

        {
          (showLogin || showSignUp) ?
            <AuthForm showLogin={showLogin} showSignUp={showSignUp} />
          : <About />
        }
      </Container>
    </>
  )
}

export default LandingSlide;