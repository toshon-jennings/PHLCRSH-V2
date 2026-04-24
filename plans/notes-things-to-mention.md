## On data gathering 

- It's interesting how disconnected and patchy this data is. Some of that is a feature - we cant get traffic counts for every road and certtainly not every year. Not through typical survey means, but obviouslyt through big data - or p2p data, we can make this happen. The trade off is perhaps precision. Goes to what Luke was saying about businesses operating off insights drawn solely off public data. Why does this matter? Because it saves time. 
- However, I can see the value in good ol fashion hitting the pavement and getting data.
- A lot of the data has some sort of twin or sibling in the crash_data set itself. That's probably okay for a lot of this, but it often isn't as precise (flags like over 55 over 65), is georefrenecd to the crash, and again, a degree of uncertainty. Makes spatial insights a bit tougher.

## Learnings

- Learning a lot looking up spatial ops in pythonm only learned in R and still need more practice
- real world spatial data
- Why cartways? A road for carts... okay.. just "A designated area for street vehichles". There's also the notion that it refers to _improved_ roadways, but clearly that's not the use here.

## On Transects

This was the toughest part of the assignment and had a lot of help. It makes sense intuitively, and I want to understand it thoroughly, so let's go through it at a high level first.

### Transect Sampling 

Transect sampling is a technique often used in ecology - you have a line through some habitat and then measure what is present along it or near it. Then you infer, hey this is swampland, or this area has the most jackrabbits. 

For this project, we're interested in geometry, not habitats. We're going to make repeated perpendicular measurements along the centerline, find out which curbs (polygons) they intersect with, and then summarize widths (not animal populations). Why perpendicular? Because that's how curbs related to centerlines. So - at this particular spot, how wide is the road?

Of course, real life is messy. Roads aren't uniform and neither is our curb cutout data. That's why we take multiple samples along each centerline segment and then use the median to reduce influence of nasty outliers.

This is a pretty intensive process - taking a while.
