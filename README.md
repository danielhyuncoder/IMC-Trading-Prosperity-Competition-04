
# IMC Prosperity 4 Writeup - Dachshund Traders

Greetings! This was my first ever IMC Prosperity competition that I competed in. Even though my results were definitely subpar and not that great, I felt like I learned a lot about what it truly takes to succeed in a quantitative trading firm: experience, discipline, and most importantly adaptability.




## Results:
My overall final IMC Prosperity 4 rank ended up as #1,273, with a vast majority of my PnL coming from the manual challenges. Having studied the past iterations of IMC Prosperity competitions, I felt that this one was by far the most challenging! I read the writeups of top teams in the past and their algorithims were definitely much simplier.

Unlike previous iterations, IMC Prosperity 4's products were much more complicated than ever before. For instance, during the options round, fitting a standard IV curve was proven to be too unstable to extract a meaningful edge from. In addition, most of the assets were not mean reverting and had significant drift. 


## Round 0
In the tutorial round of IMC Prosperity 4, I focused on building the software and tools I will be using throughout the competition. I ended up making my own custom backtester (based on the IMC Prosperity 4 documentation) in Python, along with a visualization library (that allowed me to look at inventory management, overall PnL, drawdowns, etc). I also studied past iterations of IMC Prosperity 4 such as how to fit an IV curve.

In this round, we were introduced to only two assets: Tomatoes and Emeralds. These two assets were very straightforward. Emeralds was fixed around the true fair value of around 10,000 and had significant amount of liquidity. Tomatoes was a non-stationary asset, but it also had a large amount of liquidity. For these two assets, I discovered that standard market making around their mid prices was the most optimal solution to trade these assets.

## Round 1 (Algorithimic)
In round 1 of the official competition, we were introduced to two assets: ASH_COATED_OSMIUM, and INTARIAN_PEPPER_ROOT. For ASH_COATED_OSMIUM, I quickly discovered market making was the most optimal strategy, as it is highly similar to Tomatoes. After playing around with my custom inventory limit, I figured out that an inventory of 50 would give a decent PnL with the lowest amount of drawdowns.

For INTARIAN_PEPPER_ROOT, I discovered that market making wasn't profitable at all given the upward directional trend of the asset. Due to this, I discovered that crossing the book early and maxing out the inventory of INTARIAN_PEPPER_ROOT early on was the most profitable strategy. 

## Round 1 (Manual)
In the manual challenge of round 1, we were introduced with two orderbooks of DRYLAND_FLAX and EMBER_MUSHROOM. The challenge was that we could place one order for each book, and our task was to find the most profitable way to trade these two assets. We were also garunteed that our inventory would be bought out at 30 for DRYLAND_FLAX and 20 for EMBER_MUSHROOM.

For DRYLAND_FLAX, I wrote a brute-force script where I discovered that the most profitable way to trade flax was to send a bid order of 5000 FLAX at the price of 29. I came to this logic due to the fact that there was a price-time priority in place which prevented me from placing the bid lower and securing a match from the asks.

For EMBER_MUSHROOM, I wrote another brute force script where I discoved placing a bid at the price of 18 of 35000 mushrooms was the optimal placement. For this asset, there was also a fee of 0.1 for every mushroom purchased, hence the PnL for this asset ended up being 66,500 rather than the full 70,000. 

## Results (Round 1)

After this round ended, I had made around 166,000 XIRECS in profit, which was nearly enough to qualify for the finalist rounds alone. For manual I made 71,500 XIRECS, and for my algorithim I made around 94,500 XIRECS in profit. 

## Round 2 (Algorithimic)
In round 2 of the competition, they kept both of the original assets of round 1 with a special twist: we could enter a certain bid for a extra market access for our algorithims. If our bid was higher than 50% of the bids of the rest of the teams, then we would get the extra market access. In other words, we would get extra liquidity provided for our algorithims if we placed a bid higher than the median. I ended up not touching the bid function of this round due to the potential of risk of being eliminated before the finalist rounds, and I just submitted my algorithim from round 1.

## Round 2 (Manual)
In the manual challenge for round 2, we were introduced to three variables: speed, research, and scale. We had 50,000 XIRECS to invest between the three and our job was to find the most optimal way to distribute the 50,000 XIRECS amongst the variables for the highest amount of PnL.

We were given the formula for the PnL, which was simply:

```python
PnL = (research_multiplier * scale_multiplier * speed_multiplier) - total_spent
```

We were given the formulas for Research and Scale, which I quickly converted to Python functions:




## Functions for research and speed


```python
  def research(invested: int) -> float:
    return 200000 * np.log(1 + invested) / np.log(1+100)
  def scale(invested: int) -> float:
    return (invested*7)/100
```

I recognized quickly that the function for research gave largely diminishing returns the more I invested into it. For scale, I realized that it was linear in terms of returns. Nevertheless I made a brute force script where I found out that the optimal allocation of investment of these two multipliers ALONE (ignoring the speed multiplier) was 23 and 77. Even if I invested 0 into the speed multiplier, it would garuntee give at least a multiplier of 1. 

