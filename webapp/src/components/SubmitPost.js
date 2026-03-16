import { Button, Form, Row, Col } from "react-bootstrap";
import {getToken} from "../App"
import axios from 'axios';

function SubmitPost({ updatePost }) {
    const handleSubmit = (e) => {
      e.preventDefault();
      axios.post("/posts",
        {
          title: e.target.title.value,
          body: e.target.body.value,
        },
        { headers: { Authorization: getToken() } })
        .then((res) => {
          updatePost()
        })
        .catch((error) =>{
        });
    }
    return (
      <Form onSubmit={e => { handleSubmit(e) }}>
        <Row>
          <Col>
            <Form.Group controlId="taskTile">
              <Form.Label>Title</Form.Label>
              <Form.Control type="text" placeholder="Title" name="title" />
            </Form.Group>
          </Col>
          <Col>
            <Form.Group controlId="taskBody">
              <Form.Label>Contenu</Form.Label>
              <Form.Control type="text" placeholder="Body" name="body" />
            </Form.Group>
          </Col>
          <Col className="d-flex">

            <Button variant="primary" type="submit" className='align-self-end' >
              Submit
            </Button>
          </Col>
        </Row>

      </Form>

    );
  }

export default SubmitPost;
