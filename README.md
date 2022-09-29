
# Mr. Kex

A chatbot for the fictionally existing restaurant "Karinderya Express", which caters a variety of *ulams* (viands) to serve within the fictional Manila area.

This allows to have a 1-on-1 conversation with the customer who would order through said chatbot.


## Conversational Flow Design

The green-highlighted box represents the intents which can be redirected between them.

![App Screenshot](/images/conversation-flow.png)
 
## Backend Implementation

The flow is created through Dialogflow CX. The responses by Mr. Kex are created in Google Firestore, and the way that it moves from Dialogflow to Firestore (and vice-versa) is through a webhook.

![App Screenshot](/images/backend.png)

Each time the user inquiry is recognized, Mr. Kex tries to match it to one of the intents in CX.

If there is a match, it is routed to a [Page](https://cloud.google.com/dialogflow/cx/docs/concept/page). Otherwise, it is routed to a fallback page, where a default response is awaiting to be delivered by the chatbot to the Customer.

For both matches and non-matches, a **custom_response_key** parameter (found in each Page) is sent to the webhook, matched to one of the underlying [documents](https://firebase.google.com/docs/firestore/data-model) and then returns the response back to Mr. Kex, through the webhook and CX.

## Tested Sample Inquiries

**Availability of items**

| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| What is the current stock for all items? | Here are the following items available: 2x Pork Adobo, 4x White Rice, 1x Sinigang na Bangus|
| Is your *pork adobo* available? | There are 2 servings of *pork adobo* available |
| Do you have *sinigang* available? | Sorry, we're out of *Sinigang na Bangus*.

**Price of items**
| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| How much is your *sinigang*? | It costs 40 pesos. |
| How much is the cost of all your items in the menu? | Here are the prices of each item in the menu: Sinigang na Bangus - ₱50, Tortang Talong - ₱45, Pork Adobo - ₱40, White Rice - ₱10 |  

**Current orders**

| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| What did I ordered so far? | You ordered: 1x *Sinigang na Bangus*, 1x *Tortang Talong* and 1x white rice. |
| Can you recap to me what I ordered? | You ordered: 2x *Pork Adobo*, 1x *Sinigang na Bangus* and 2x white rice. |

## Limitations

- Restaurant menu is limited to 4 items:
    - *Tortang talong*
    - *Sinigang na bangus*
    - *Pork adobo*
    - *Kanin* (white rice)
- Pickup only
- English inquiries are only accepted
- The following inquiries are not yet tested for the chatbot, but not necessarily will provide the most accurate answer:
    - What is the cost of a serving of *torta* and 2 cups of white rice? (1 *torta* + 2 rice)
    - Do you have 1 cup of *adobo* and white rice available? (1 *adobo* + 1 rice)
    - I'll order 2 *pork adobo*, 3 *sinigang* and white rice. (3 white rice too?)
- Unable to immediately message the Customer should KarinderyaExpress have no viands available
- Unable to answer follow-up questions (i.e. How much is this item?)
- Unable to answer questions regarding the total amount to be paid out
- Customer can add items to an order through Mr. Kex, but not remove or change existing ones
## To-do

- Implement and test the following:
    - [ ]  CX Routes for follow-up questions
    - [ ]  Providing only the total cost of the items ordered
    - [ ]  Sending an order to Firestore
    - [ ]  Removing items in an order
    - [ ]  Changing items in an order
- [ ]  Resolve the fourth to the last limitation, if possible