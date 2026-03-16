import { Badge, Card, Col, ListGroup, CloseButton, Button, ProgressBar } from "react-bootstrap";
import React, { useEffect, useState } from 'react';
import { getToken } from "../App"
import axios from 'axios';

function Post({ post, removePost, updatePost }) {
    const [showCard, setShowCard] = useState(true);
    const [attachment, setAttachment] = useState(null);
    const [image, setImage] = useState(null);
    const [labeling, setLabeling] = useState(null)

    const fileChanged = (e) => {
        const files = e.target.files || e.dataTransfer.files;
        if (!files.length) return;
        setAttachment(files[0]);
    }
    const getSignedUrlPut = async (postId, filetype) => {
        const config = {
            headers: { Authorization: getToken() },
            params: {
                filename: attachment.name,
                filetype: filetype,
                postId: postId,
            },
        };

        const response = await axios.get("/signedUrlPut", config);
        const uploadURL = response.data?.uploadURL;
        if (!uploadURL) {
            throw new Error("Backend na pas renvoye uploadURL. Reponse: " + JSON.stringify(response.data));
        }
        return new URL(uploadURL);
    }
    const submitFile = async () => {
        if (!attachment) {
            alert("Please select a file to upload.");
            return;
        }
        try {
            const postId = post.id.split("#")[1];
            const filetype = attachment.type || "application/octet-stream";
            const uploadUrl = await getSignedUrlPut(postId, filetype);

            const config = {
                headers: { "Content-Type": filetype },
            };
            const putUrl = typeof uploadUrl === "string" ? uploadUrl : uploadUrl.href;

            var instance = axios.create();
            delete instance.defaults.headers.common['Authorization'];
            setLabeling(true);

            try {
                const res = await instance.put(putUrl, attachment, config);
                setTimeout(() => {
                    setLabeling(false);
                    updatePost();
                }, 2000);
            } catch (putErr) {
                setLabeling(false);
                if (putErr.message === "Network Error" || !putErr.response) {
                    alert("Erreur reseau lors de l'upload vers S3. Le backend a repondu (signedUrlPut 200) mais la requete PUT vers le bucket S3 echoue. Onglet Network : requete vers amazonaws.com (CORS ou statut).");
                } else {
                    alert(putErr.response?.data?.detail ?? putErr.message);
                }
                return;
            }
        } catch (err) {
            setLabeling(false);
            const msg = err.response?.data?.detail ?? err.message;
            if (err.message === "Network Error" || !err.response) {
                const base = axios.defaults.baseURL || "(non défini)";
                alert(`Erreur réseau : le backend ne répond pas.\n\nBaseURL actuelle : ${base}\n\n• Vérifiez que cette URL s’ouvre dans le navigateur (ex. ${base}/posts).\n• Si oui, ouvrez les Outils de développement (F12) → Network, réessayez l’upload et regardez la requête « signedUrlPut » (statut et erreur CORS).`);
            } else {
                alert(Array.isArray(msg) ? msg.join(" ") : msg);
            }
        }
    }

    const deletePost = async () => {
        const id = post.id.split("#")[1];
        axios.delete(`/posts/${id}`, { headers: { Authorization: getToken() } })
            .then(res => {
                setShowCard(false);
            })
            .catch((error) =>{
            });

    };

    return (<>
        {showCard && (
            <Col>
                <Card style={{ marginTop: '1rem', }} key={post.id}>
                    <Card.Header >{post.title} <CloseButton className="float-end" onClick={deletePost} /></Card.Header>
                    <Card.Img variant="top" src={post.image} />
                    <Card.Body>
                        <Card.Text>
                            {post.body}
                        </Card.Text>
                    </Card.Body>
                    <ListGroup variant="flush">
                        {post.labels
                            ?
                            <ListGroup.Item>

                                {post.labels.map((label) => (
                                    <Badge key={label} bg="info">
                                        {label}
                                    </Badge>
                                ))}{' '}
                            </ListGroup.Item>
        
                            : 
                            <ListGroup.Item>
                                Attachment:
                                <input type="file" onChange={fileChanged} />
                                <Button
                                    variant="primary"
                                    onClick={submitFile}
                                >
                                    Upload
                                </Button>
                                {labeling &&
                                <ProgressLabeling/>
                                }
                            </ListGroup.Item>
                            }
                    </ListGroup>
                </Card>
            </Col>
        )}
    </>
    )
}

function ProgressLabeling() {
    const [progress, setProgress] = useState(0);
  
    useEffect(() => {
      const timer = setInterval(() => {
        if (progress < 100) {
          setProgress(progress + 1);
        }
      }, 10);
  
      return () => {
        clearInterval(timer);
      };
    }, [progress]);
  
    return (
      <div className="App">
        <ProgressBar now={progress} label="Detecting labels" />
      </div>
    );
  }
  


export default Post