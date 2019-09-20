from core_modules.logger import initlogging
from core_modules.helpers import require_true
from core_modules.settings import NetWorkSettings


class ArtWork:
    def __init__(self, artid, txid, finalactticket, regticket):
        self.artid = artid
        self.txid = txid
        self.finalactticket = finalactticket
        self.regticket = regticket


class TicketWrapper:
    def __init__(self, blockheight, artid, txid, tickettype, ticket):
        self.created = blockheight
        self.artid = artid
        self.txid = txid
        self.ticket = ticket
        self.tickettype = tickettype
        self.status = None                          # open, locked, done, invalid
        self.done = None

    def __str__(self):
        return "TXID: %s" % self.txid

    def expired(self, current_block_height):
        require_true(self.tickettype == "trade")

        if self.ticket.expiration != 0:
            blocks_elapsed = current_block_height - self.created
            if blocks_elapsed > self.ticket.expiration:
                return True
        return False


class Match:
    def __init__(self, logger, artid, bid, ask, lockstart):
        self.__logger = logger

        self.artid = artid
        self.bid = bid
        self.ask = ask

        # sanity check
        if self.bid.ticket.type != "bid" or self.ask.ticket.type != "ask":
            raise ValueError("Bid is not bid or Ask is not ask!")

        # these two variables mark the block numbers in between which this match is considered valid
        self.lockstart = lockstart
        self.lockend = lockstart + NetWorkSettings.TICKET_MATCH_EXPIRY

    def __str__(self):
        return "art: %s, bid: %s, ask: %s" % (self.artid.hex(), self.bid, self.ask)

    def lock(self):
        self.__logger.debug("%s Tickets locked: %s, %s" % (self.artid.hex(), self.bid, self.ask))
        self.bid.status = "locked"
        self.ask.status = "locked"

    def unlock(self, success, current_block_height):
        if success:
            self.bid.status = "done"
            self.bid.done = True
            self.ask.status = "done"
            self.ask.done = True
            self.__logger.debug("%s Successful match, tickets are done: %s, %s" % (self.artid.hex(), self.bid, self.ask))
        else:
            # unsuccessful match, bid ticket is invalidated
            self.bid.status = "invalid"
            self.bid.done = True
            self.__logger.debug("%s Unsuccessful match, second ticket is invalid %s, height: %s" % (
                self.artid.hex(), self.ask, current_block_height))

            # check if ticket has expired
            if self.ask.expired(current_block_height):
                self.ask.status = "invalid"
                self.ask.done = True
                self.__logger.debug("%s Unsuccessful match, first ticket expired: %s, height: %s" % (
                    self.artid.hex(), self.ask, current_block_height))
            else:
                self.ask.status = "open"
                self.__logger.debug("%s Unsuccessful match, first ticket remains open: %s, height: %s" % (
                    self.artid.hex(), self.ask, current_block_height))

    def expired(self, current_block_height):
        if current_block_height > self.lockend:
            return True
        return False


class ArtRegistry:
    def __init__(self, nodenum):
        self.__logger = initlogging('', __name__)
        self.__artworks = {}
        self.__tickets = {}
        self.__owners = {}
        self.__matches = []
        self.__current_block_height = None

    def __unlock_match(self, match, success):
        match.unlock(success=success, current_block_height=self.__current_block_height)

    def __invalidate_ticket(self, ticket):
        artid = ticket.artid
        ticket.status = "invalid"
        ticket.done = True

        # unlock the copies if ask
        artdb = self.__owners[artid]
        if ticket.ticket.type == "ask":
            artdb[ticket.ticket.public_key] += ticket.ticket.copies

    def update_current_block_height(self, new_height):
        self.__current_block_height = new_height

        unlocked_tickets = []

        # invalidate matches that expired
        newmatches = []
        for match in self.__matches:
            if match.expired(self.__current_block_height):
                # match has expired without valid transaction
                self.__unlock_match(match, False)
                self.__logger.debug("Match has expired: %s, height: %s" % (match, self.__current_block_height))

                # if match.ask has not expired add it back to the matcher engine
                if match.ask.done is not True:
                    unlocked_tickets.append(match.ask)
            else:
                newmatches.append(match)
        self.__matches = newmatches

        # invalidate open tickets (only these can expire)
        for artid in self.__artworks.keys():
            for ticket in self.__get_open_trade_tickets_for_art(artid):
                if ticket.expired(self.__current_block_height):
                    self.__invalidate_ticket(ticket)
                    self.__logger.debug("Ticket has expired: %s" % ticket)

        # add back freshly unlocked tickets to the matcher engine
        for ticket in unlocked_tickets:
            self.__find_match(ticket)

    def process_watched_vout(self, address, value):
        self.__logger.debug("Relevant transaction received for address %s with value %s" % (address, value))

        found = None
        for match in self.__matches:
            ask = match.ask
            bid = match.bid

            if ask.ticket.watched_address == address and ask.ticket.price * ask.ticket.copies == value:
                self.__unlock_match(match, True)

                # assign artwork over to the new owner
                artdb = self.__owners[match.artid]
                new_owner = bid.ticket.public_key
                if artdb.get(new_owner) is None:
                    artdb[new_owner] = 0
                artdb[new_owner] += bid.ticket.copies

                self.__logger.debug("%s Consummation successful for txid %s, %s copies reassigned from %s to %s!" % (
                    match.artid, ask.txid, ask.ticket.copies, ask.ticket.public_key.hex(), bid.ticket.public_key.hex()))
                found = match
                break

        if found is not None:
            self.__matches.remove(found)

    def process_watched_vin(self, utxo_txid):
        self.__logger.debug("Relevant transaction received for utxo %s" % utxo_txid)

        for ticketwrapper in self.get_all_tickets_watched_for_collateral():
            # find the ticket for the utxo
            if ticketwrapper.ticket.collateral_txid == utxo_txid:
                self.__logger.debug("UTXO movement detected for txid %s" % utxo_txid)

                # check if ticket is part of a match
                match = None
                if ticketwrapper.status == "locked":
                    # find match
                    for m in self.__matches:
                        if m.bid is ticketwrapper:
                            match = m
                            break

                # if it is, unlock the match
                if match is not None:
                    self.__logger.debug("UTXO movement (txid: %s) found in active match, unlocking match" % utxo_txid)
                    self.__unlock_match(match, False)

                    # remove match
                    newmatches = [m for m in self.__matches if m is not match]
                    self.__matches = newmatches

                # close the ticket
                self.__invalidate_ticket(ticketwrapper)
                self.__logger.debug("Invalidated ticket %s due to UTXO movement: %s" % (ticketwrapper.ticket,
                                                                                        utxo_txid))

    def get_listen_addresses_and_utxos(self):
        addresses, utxos = set(), set()

        # we watch match deposit addresses for consummation
        for match in self.__matches:
            addresses.add(match.ask.ticket.watched_address)

        # we watch all bid tickets for collateral movement
        for ticketwrapper in self.get_all_tickets_watched_for_collateral():
            utxos.add(ticketwrapper.ticket.collateral_txid)

        return addresses, utxos

    def add_artwork(self, txid, finalactticket, regticket):
        artid = regticket.imagedata_hash
        self.__artworks[artid] = ArtWork(artid, txid, finalactticket, regticket)
        self.__logger.debug("FinalActivationTicket added to artregistry: %s" % finalactticket)

        # update owner DB
        if self.__owners.get(artid) is None:
            self.__owners[artid] = {}
            self.__tickets[artid] = []
        artdb = self.__owners[artid]

        # assert that this artwork is not yet found
        require_true(artdb.get(regticket.author) is None)

        artdb[regticket.author] = regticket.total_copies
        self.__logger.debug("Author %s granted %s copies" % (regticket.author, regticket.total_copies))

    def add_transfer_ticket(self, txid, ticket):
        artid = ticket.imagedata_hash
        artdb = self.__owners[artid]
        author_copies = artdb.get(ticket.public_key)

        # validate that enough copies exist
        if author_copies > ticket.copies:
            wrappedticket = TicketWrapper(self.__current_block_height, artid, txid, "transfer", ticket)
            self.__tickets[artid].append(wrappedticket)
            self.__logger.debug("Transfer ticket added to artregistry: %s" % ticket)

            # enough copies exist, transfer them
            if artdb.get(ticket.recipient) is None:
                artdb[ticket.recipient] = 0

            # move the copies
            artdb[ticket.recipient] += ticket.copies
            artdb[ticket.public_key] -= ticket.copies
            self.__logger.debug("Copies updated: %s -> %s, %s -> %s" % (ticket.recipient, artdb[ticket.recipient],
                                                                        ticket.public_key, artdb[ticket.public_key]))
            wrappedticket.done = True
            wrappedticket.status = "done"
        else:
            self.__logger.debug("Not enough copies exist %s <= %s, skipping ticket" % (author_copies, ticket.copies))

    def add_trade_ticket(self, txid, ticket):
        artid = ticket.imagedata_hash

        # lock up artworks in the trade if ask and valid
        if ticket.type == "ask":
            artdb = self.__owners[artid]
            if artdb.get(ticket.public_key) is None or ticket.copies > artdb[ticket.public_key]:
                self.__logger.debug("Artist tried to sell more art than they have, ignoring ticket!")
                return
            self.__logger.debug("Ask ticket locked %s artworks from %s" % (ticket.copies, ticket.public_key.hex()))
            artdb[ticket.public_key] -= ticket.copies

        # create a new wrapped ticket
        wrappedticket = TicketWrapper(self.__current_block_height, artid, txid, "trade", ticket)
        wrappedticket.done = False
        wrappedticket.status = "open"
        self.__tickets[artid].append(wrappedticket)
        self.__logger.debug("Open trade ticket added to artregistry: %s" % ticket)

        # try to find matches for this ticket
        self.__find_match(wrappedticket)

    def __get_open_trade_tickets_for_art(self, artid):
        ret = []
        for ticket in self.__tickets[artid]:
            if ticket.tickettype == "trade" and ticket.status == "open":
                ret.append(ticket)
        return ret

    def __find_match(self, newticket):
        tickets = self.__get_open_trade_tickets_for_art(newticket.artid)
        for matchticket in tickets:
            if matchticket.ticket.price == newticket.ticket.price\
            and matchticket.ticket.copies == newticket.ticket.copies\
            and matchticket.ticket.public_key != newticket.ticket.public_key\
            and ((matchticket.ticket.type == "ask" and newticket.ticket.type == "bid") or
                 (matchticket.ticket.type == "bid" and newticket.ticket.type == "ask")):

                # match found
                self.__logger.debug("Ticket match found at price %s, copies: %s" % (
                    newticket.ticket.price, newticket.ticket.copies))

                # tickets matched, add a match object and lock
                if matchticket.ticket.type == "ask":
                    ask = matchticket
                    bid = newticket
                else:
                    ask = newticket
                    bid = matchticket

                match = Match(self.__logger, newticket.artid, bid, ask, self.__current_block_height)
                match.lock()

                self.__matches.append(match)
                self.__logger.debug("Match found between %s and %s" % (matchticket.txid, newticket.txid))

                return matchticket
        return None

    def enough_copies_left(self, artid, author, copies):
        artdb = self.__owners.get(artid)
        if artdb is None:
            return False

        author_copies = artdb.get(author)
        if author_copies is None or author_copies < copies:
            return False

        return True

    def get_art_owned_by(self, pubkey):
        artworks = []
        for artid, owners in self.__owners.items():
            for owner, copies in owners.items():
                if owner == pubkey:
                    artworks.append((artid, copies))
        return artworks

    def get_trades_for_automatic_consummation(self):
        from start_single_masternode import pastelid
        ret = []
        for match in self.__matches:
            # find matches that are in the locked state
            if match.ask.status == "locked":
                # if the bid belongs to us
                # FIXME: probably match.bid.ticket.public_key need to be replaced with match.bid.ticket.pastelid,
                # FIXME: and pastelid should be added to the ticket
                if match.bid.ticket.public_key == pastelid:
                    # return the wallet address and total price
                    ret.append((match.ask.ticket.watched_address, match.ask.ticket.price * match.ask.ticket.copies))
        return ret

    def get_all_tickets_watched_for_collateral(self):
        ret = set()
        for artid in self.__artworks.keys():
            for ticketwrapper in self.__tickets[artid]:
                # if this ticket is a trade ticket, is open or locked, is mine and is a bid
                if ticketwrapper.tickettype == "trade" \
                and ticketwrapper.status in ["open", "locked"] \
                and ticketwrapper.ticket.type == "bid":
                    ret.add(ticketwrapper)
        return ret

    def get_all_collateral_utxo_for_pubkey(self, pubkey):
        ret = set()
        for ticketwrapper in self.get_all_tickets_watched_for_collateral():
            if ticketwrapper.ticket.public_key == pubkey:
                ret.add(ticketwrapper.ticket.collateral_txid)
        return ret

    def get_my_trades_for_artwork(self, pubkey, artid):
        ret = []

        if artid in self.__tickets:
            for ticketwrapper in self.__tickets[artid]:
                if ticketwrapper.ticket.public_key == pubkey:
                    ret.append(self.__ticket_to_django_format(ticketwrapper))
        return ret

    def get_ticket_for_artwork(self, artid):
        return self.__artworks[artid].finalactticket

    def get_all_artworks(self):
        artworks = []
        for artid, artwork in self.__artworks.items():
            artworks.append((artid, artwork.regticket.to_dict()))
        return artworks

    def get_art_owners(self, artid):
        artdb = self.__owners.get(artid)
        if artdb is None:
            return {}

        return artdb.copy()

    def get_art_trade_tickets(self, artid):
        tradetickets = self.__tickets.get(artid)
        if tradetickets is None:
            return None

        ret = []
        for ticketwrapper in tradetickets:
            ret.append(self.__ticket_to_django_format(ticketwrapper))
        return ret

    def __ticket_to_django_format(self, ticketwrapper):
        return (ticketwrapper.created, ticketwrapper.txid, ticketwrapper.done, ticketwrapper.status,
                ticketwrapper.tickettype, ticketwrapper.ticket.to_dict())
