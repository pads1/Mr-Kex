
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

**Introduction**

1st Chatbot Response | User Inquiry | 2nd Chatbot Response |
| ----------- | ----------- | ----------- |
| Hello. What is your full name? | My name is Mandy Roco. | Hello Mandy Roco! I am Mr. Kex, your assistant to help you in introducing to Karinderya Express, your one-stop shop to all of the classic Filipino karinderya favorites. <br><br>We currently have Pork Adobo, Sinigang na Bangus, and Tortang Talong for our ulams. White rice is on the side. <br><br> Can I take your order? |

**Checking availability of items**

| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| What is the current stock for all items? | Here are the following items available: 2x Pork Adobo, 4x White Rice, 1x Sinigang na Bangus|
| Is your *pork adobo* available? | There are 2 servings of *pork adobo* available |
| Do you have *sinigang* available? | Sorry, we're out of *Sinigang na Bangus*.

**Checking price of items**
| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| How much is your *sinigang*? | It costs 40 pesos. |
| How much is the cost of all your items in the menu? | Here are the prices of each item in the menu: Sinigang na Bangus - ₱50, Tortang Talong - ₱45, Pork Adobo - ₱40, White Rice - ₱10 |  

**Current orders**

| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| What did I ordered so far? | You ordered: 1x *Sinigang na Bangus*, 1x *Tortang Talong* and 1x white rice. |
| Can you recap to me what I ordered? | You ordered: 2x *Pork Adobo*, 1x *Sinigang na Bangus* and 2x white rice. |

**Placing orders**

| User Inquiry | Chatbot Response |
| ----------- | ----------- |
| I would like to order 2 cups of sinigang and 1 pork adobo. | Okay. Anything else? |

## Limitations

- Restaurant menu is limited to 4 items:
    - *Tortang talong*
    - *Sinigang na bangus*
    - *Pork adobo*
    - *Kanin* (white rice)
- Pickup only
- English inquiries are only accepted
- Inquiries that ask for an item's availability and cost are not responded well by Mr. Kex
- Unable to immediately message the Customer should KarinderyaExpress have no items available
- Customer can add and remove items to an order through Mr. Kex, but not change existing ones
- Some responses are not perfectly well-constructed
- Follow-up questions are only responded well when it is in the same topic (i.e. availability of 1 *torta* and 1 rice, then availability of 1 *sinigang*), and not on the same menu item (i.e. availability of *torta*, then its cost)

## To-do

- [x]  CX Routes for follow-up questions
- [x]  Providing only the total cost of the items ordered
- [x]  Sending an order to Firestore
- [x]  Removing items in an order
- [x]  Resolving complex inquiries (i.e. quantity+viand, quantity+viand+viand), if possible
- [ ]  Testing with the UI integration