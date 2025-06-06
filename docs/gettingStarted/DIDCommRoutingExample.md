# DIOComm Routing - an example

In this example, we'll walk through an example of complex DIDComm routing, outlining some of the possibilities that can be implemented. Do realize that
the vast majority of the work is already done for you if you are just using ACA-Py. You have to define the setup your agents will use, and ACA-Py will take care of all the messy details described below.

We'll start with the Alice and Bob example from the [Cross Domain Messaging](https://github.com/decentralized-identity/aries-rfcs/tree/main/concepts/0094-cross-domain-messaging) Aries RFC.

![Cross Domain Messaging Example](https://raw.githubusercontent.com/hyperledger/aries-rfcs/main/concepts/0094-cross-domain-messaging/domains.jpg "Cross Domain Messaging Example")

What are the DIDs involved, what's in their DIDDocs, and what communications are happening between the agents as the connections are made?

## The Scenario

Bob and Alice want to establish a connection so that they can communicate. Bob uses an Agency endpoint (`https://agents-r-us.ca`), labelled as 9 and will have an agent used for routing, labelled as 3. We'll also focus on Bob's messages from his main iPhone, labelled as 4.  We'll ignore Bob's other agents (5 and 6) and we won't worry about Alice's configuration (agents 1, 2 and 8). While the process below is all about Bob, Alice and her agents are doing the same interactions within her domain.

## All the DIDs

A DID and DIDDoc are generated by each participant in each relationship. For Bob's agents (iPhone and Routing), that includes:

- Bob and Alice
- Bob and his Routing Agent
- Bob and Agency
- Bob's Routing Agent and Agency

That's a lot more than just the Bob and Alice relationship we usually think about!

## DIDDoc Data

From a routing perspective the important information in the DIDDoc is the following (as defined in the [DIDDoc Conventions Aries RFC](https://github.com/decentralized-identity/aries-rfcs/tree/main/features/0067-didcomm-diddoc-conventions/README.md)):

- The public keys for agents referenced in the routing
- The `services` of type `did-communication`, including:
  - the one `serviceEndpoint`
  - the `recipientKeys` array of referenced keys for the ultimate target(s) of the message
  - the `routingKeys` array of referenced keys for the mediators

Let's look at the `did-communication` service data in the DIDDocs generated by Bob's iPhone and Routing agents, listed above:

- Bob and Alice:
  - The `serviceEndpoint` that Bob tells Alice about is the endpoint for the Agency.

    - We'll use for the endpoint the Agency's public DID. That way the Agency can change rotate the keys for the endpoint without all of its clients from having to update every DIDDoc with the new key.

  - The `recipientKeys` entry is a key reference for Bob's iPhone specifically for Alice.
  - The `routingKeys` entries is a reference to the public key for the Routing Agent.

- Bob and his Routing Agent:
  - The `serviceEndpoint` is empty because Bob's iPhone has no endpoint. See the note below for more on this.
  - The `recipientKeys` entry is a key reference for Bob's iPhone specifically for the Routing Agent.
  - The `routingKeys` array is empty.

- Bob and Agency:
  - The `serviceEndpoint` is the endpoint for Bob's Routing Agent.
  - The `recipientKeys` entry is a key reference for Bob's iPhone specifically for the Agency.
  - The `routingKeys` is a single entry for the key reference for the Routing Agent key.

- Bob's Routing Agent and Agency:
  - The `serviceEndpoint` is the endpoint for Bob's Routing Agent.
  - The `recipientKeys` entry is a key reference for Bob's Routing Agent specifically for the Agency.
  - The `routingKeys` array is empty.

The null `serviceEndpoint` for Bob's iPhone is worth a comment. Mobile apps work by sending requests to servers, but cannot be accessed directly from a server. A DIDComm mechanism ([Transports Return Route](https://github.com/decentralized-identity/aries-rfcs/tree/main/features/0092-transport-return-route)) enables a server to send messages to a Mobile agent by putting the messages into the response to a request from the mobile agent. While not formalized in an Aries RFC (yet), cloud agents can use mobile platforms' (Apple and Google) notification mechanisms to trigger a user interface event.

## Preparing Bob's DIDDoc for Alice

Given that background, let's go through the sequence of events and messages that occur in building a DIDDoc for Bob's edge agent to send to Alice's edge agent. We'll start the sequence with all of the Agents in place as the bootstrapping of the Agency, Routing Agent and Bob's iPhone is trickier than we need to go through here. We'll call that an "exercise left for the reader".

We'll start the process with Alice sending an out of band connection invitation message to Bob, e.g. through a QR code or a link in an email. Here's one possible sequence for creating the DIDDoc. Note that there are other ways this could be done:

- Bob's iPhone agent generates a new DID for Alice and prepares, and partially completes, a DIDDoc
- Bob messages the Routing Agent to send the newly created DID and to get a new public key for the Alice relationship.
  - The Routing Agent records the DID for Alice and the keypair to be used for messages from Alice.
- The Routing Agent sends the DID to the Agency to let the Agency know that messages for the new DID are to go to the Routing Agent.
- The Routing Agent sends the data to Bob's iPhone agent.
- Bob's iPhone agent fills in the rest of the DIDDoc:
  - the public key for the Routing Agent for the Alice relationship
  - the `did-communication` service endpoint is set to the Agency public DID and
  - the routing keys array with the values of the Agency public DID key reference and the Routing Agent key reference

**Note**: Instead of using the DID Bob created, the Agency and Routing Agent might use the public key used to encrypt the messages for their internal routing table look up for where to send a message. In that case, the Bob and the Routing Agent share the public key instead of the DID to their respective upstream routers.

With the DIDDoc ready, Bob uses the path provided in the invitation to send a `connection-request` message to Alice with the new DID and DIDDoc. Alice now knows how to get any DIDComm message to Bob in a secure, end-to-end encrypted manner. Subsequently, when Alice sends messages to Bob's agent, she uses the information in the DIDDoc to securely send the message to the Agency endpoint, it is sent through to the Routing Agent and on to Bob's iPhone agent for processing. Now Bob has the information he needs to securely send any DIDComm message to Alice in a secure, end-to-end encrypted manner.

At this time, there are **not** specific DIDComm protocols for the "set up the routing" messages between the agents in Bob's domain (Agency, Routing and iPhone). Those could be implemented to be proprietary by each agent provider (since it's possible one vendor would write the code for each of those agents), but it's likely those will be specified as open standard DIDComm protocols.

Based on the DIDDoc that Bob has sent Alice, for her to send a DIDComm message to Bob, Alice must:

- Prepare the message for Bob's Agent.
- Encrypt and place that message into a "Forward" message for Bob's Routing Agent.
- Encrypt and send the "Forward" message to Bob's Agency endpoint.
